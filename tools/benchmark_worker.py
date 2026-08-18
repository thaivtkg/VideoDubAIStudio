import argparse
import json
import time
import subprocess
import sys
import os

def get_gpu_vram_used():
    """Lấy lượng VRAM (MB) đang sử dụng trên GPU qua nvidia-smi"""
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"], 
            encoding="utf-8"
        )
        return int(result.strip().split('\n')[0])
    except Exception:
        return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True, help="Tên engine (ví dụ: musetalk)")
    parser.add_argument("--duration", type=int, default=8, help="Thời lượng test (giây)")
    parser.add_argument("--fp16", action="store_true", help="Bật chế độ FP16")
    args = parser.parse_args()

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    worker_script = os.path.join(root_dir, "ai", "lipsync", "workers", f"{args.engine}_worker.py")
    
    if not os.path.exists(worker_script):
        print(json.dumps({"status": "error", "message": f"Không tìm thấy file worker: {worker_script}"}))
        sys.exit(1)

    # Ưu tiên test_<duration>s.mp4, nếu không có thì fallback sang test.mp4
    video_path = os.path.join(root_dir, f"test_{args.duration}s.mp4")
    if not os.path.exists(video_path):
        video_path = os.path.join(root_dir, "test.mp4")
        
    audio_path = os.path.join(root_dir, "test_audio.wav")
    face_json = os.path.join(root_dir, "test_face_cache.json")
    output_path = os.path.join(root_dir, f"benchmark_output_{args.engine}_{args.duration}s.mp4")

    # Tự động tạo face cache giả lập nếu chưa có
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

    start_vram = get_gpu_vram_used()
    peak_vram = start_vram
    start_time = time.time()

    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding="utf-8"
        )
        
        while process.poll() is None:
            current_vram = get_gpu_vram_used()
            if current_vram > peak_vram:
                peak_vram = current_vram
            time.sleep(0.5)
            
        stdout, stderr = process.communicate()
        end_time = time.time()
        
        worker_result = {}
        try:
            lines = stdout.strip().split('\n')
            for line in reversed(lines):
                if line.startswith('{') and line.endswith('}'):
                    worker_result = json.loads(line)
                    break
        except Exception:
            pass

        if process.returncode != 0:
            print(json.dumps({
                "status": "error",
                "message": "Worker bị lỗi hoặc tràn VRAM (OOM)",
                "stderr": stderr,
                "stdout": stdout,
                "peak_vram_mb": peak_vram
            }, indent=2, ensure_ascii=False))
            sys.exit(1)

        print(json.dumps({
            "status": "success",
            "engine": args.engine,
            "duration_tested_sec": args.duration,
            "execution_time_sec": round(end_time - start_time, 2),
            "peak_vram_allocated_mb": peak_vram - start_vram,
            "system_peak_vram_mb": peak_vram,
            "worker_metrics": worker_result,
            "output_valid": os.path.exists(output_path)
        }, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2, ensure_ascii=False))
        sys.exit(1)
        
    finally:
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass

if __name__ == "__main__":
    main()