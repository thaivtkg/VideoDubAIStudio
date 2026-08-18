import argparse
import json
import time
import subprocess
import sys
import os
import cv2

def get_gpu_vram_used():
    """Lấy VRAM hệ thống thực tế. Phục vụ tính toán Baseline để bóc tách VRAM của tiến trình ngầm."""
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"], 
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return int(result.strip().split('\n')[0])
    except Exception:
        return 0

def validate_video_artifact(file_path):
    """Kiểm định chất lượng output (Không chỉ dựa vào exit_code == 0)"""
    if not os.path.exists(file_path):
        return False, "File không tồn tại"
    if os.path.getsize(file_path) == 0:
        return False, "File rỗng (0 bytes)"
    
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return False, "Codec hỏng hoặc không thể đọc file video"
        
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = frames / fps if fps > 0 else 0
    ret, _ = cap.read()
    cap.release()
    
    if frames <= 0 or duration <= 0 or not ret:
        return False, "Video không có luồng hình ảnh (Empty frames)"
        
    return True, "Valid"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--duration", type=int, default=8)
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    worker_script = os.path.join(root_dir, "ai", "lipsync", "workers", f"{args.engine}_worker.py")
    
    video_path = os.path.join(root_dir, f"test_{args.duration}s.mp4")
    if not os.path.exists(video_path):
         video_path = os.path.join(root_dir, "test.mp4")
    audio_path = os.path.join(root_dir, "test_audio.wav")
    face_json = os.path.join(root_dir, "test_face_cache.json")
    output_path = os.path.join(root_dir, f"benchmark_output_{args.engine}_{args.duration}s.mp4")

    # Mồi cache giả lập nếu chưa có
    if not os.path.exists(face_json):
        dummy_frames = {str(i): [100, 100, 200, 200] for i in range(args.duration * 25)}
        with open(face_json, "w", encoding="utf-8") as f:
            json.dump({"frames": dummy_frames}, f)

    if os.path.exists(output_path):
        try: os.remove(output_path)
        except: pass

    cmd = [
        sys.executable, worker_script,
        "--video", video_path,
        "--audio", audio_path,
        "--face_json", face_json,
        "--output", output_path,
        "--device", "cuda",
        "--batch_size", "1"
    ]
    if args.fp16:
        cmd.append("--fp16")

    # [FIX REVIEW 2]: Chụp Baseline VRAM trước khi chạy để đo lường chênh lệch (Attribution)
    baseline_vram = get_gpu_vram_used()
    peak_vram = baseline_vram

    startup_start = time.time()
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding="utf-8"
        )
        startup_sec = round(time.time() - startup_start, 2)
        
        while process.poll() is None:
            current_vram = get_gpu_vram_used()
            if current_vram > peak_vram:
                peak_vram = current_vram
            time.sleep(0.5)
            
        stdout, stderr = process.communicate()
        total_sec = round(time.time() - startup_start, 2)
        
        exit_code = process.returncode
        
        # [FIX REVIEW 2]: Phân loại rạch ròi OOM và Crash
        oom_signatures = ["CUDA out of memory", "OOM", "Allocation on device"]
        oom = any(sig in stdout or sig in stderr for sig in oom_signatures)
        crashed = exit_code != 0 and not oom
        
        worker_result = {}
        for line in reversed(stdout.strip().split('\n')):
            if line.startswith('{') and line.endswith('}'):
                try:
                    worker_result = json.loads(line)
                    break
                except: pass
        
        # [FIX REVIEW 2]: Kiểm định Output Artifact bằng OpenCV
        output_valid, val_msg = False, "Tiến trình thất bại"
        if exit_code == 0:
            output_valid, val_msg = validate_video_artifact(output_path)
        
        frames_processed = worker_result.get("frames_processed", 0)
        fps = round(frames_processed / total_sec, 2) if total_sec > 0 else 0
        
        # Báo cáo chuẩn Form yêu cầu từ Reviewer
        report = {
            "engine": f"{args.engine}_v15",
            "duration_sec": args.duration,
            "startup_sec": startup_sec,
            "model_load_sec": worker_result.get("model_load_sec", 0), # Sẽ cập nhật từ worker ở sprint sau
            "inference_sec": worker_result.get("inference_sec", total_sec),
            "total_sec": total_sec,
            "fps": fps,
            "baseline_vram_mb": baseline_vram,
            "peak_system_vram_mb": peak_vram,
            "peak_vram_allocated_mb": peak_vram - baseline_vram, # Delta VRAM chuẩn
            "oom": oom,
            "crashed": crashed,
            "exit_code": exit_code,
            "output_valid": output_valid,
            "validation_message": val_msg
        }
        
        print(json.dumps(report, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "engine": f"{args.engine}_v15",
            "duration_sec": args.duration,
            "crashed": True,
            "exit_code": -1,
            "error_message": str(e)
        }, indent=2, ensure_ascii=False))
        
    finally:
        # Nếu muốn giữ video để test, hãy comment dòng dưới
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass

if __name__ == "__main__":
    main()