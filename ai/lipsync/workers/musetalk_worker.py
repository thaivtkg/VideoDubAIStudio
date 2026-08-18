import argparse
import json
import sys
import os
import subprocess
import shutil
import glob
import tempfile
import uuid

def get_real_device(device_policy):
    """Phân giải policy 'auto' thành 'cuda' hoặc 'cpu'"""
    if device_policy == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"
    return device_policy

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--face_json", required=True)
    parser.add_argument("--output", required=True)
    
    # Configuration thực tế từ Manager
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--face_size", type=int, default=256)
    parser.add_argument("--quality", default="balanced")
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()

    vendor_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../vendor/MuseTalk"))
    inference_script = os.path.join(vendor_path, "scripts", "inference.py")
    
    # 1. TIÊU DIỆT RACE CONDITION: Tạo Job ID và thư mục result độc lập
    job_id = str(uuid.uuid4())[:8]
    job_result_dir = os.path.join(vendor_path, "results", f"job_{job_id}")
    os.makedirs(job_result_dir, exist_ok=True)
    
    tmp_cfg_path = None

    try:
        # 2. XÁC ĐỊNH THIẾT BỊ (DEVICE POLICY)
        actual_device = get_real_device(args.device)
        
        # 3. ĐỌC FACE CACHE & TÍNH TOÁN METRICS THẬT
        frames_processed = 0
        faces_detected = 0
        
        if os.path.exists(args.face_json):
            with open(args.face_json, "r", encoding="utf-8") as f:
                face_data = json.load(f)
                # Parse format cache S4.10 mới: {"frames": {"0": [...], "1": [...]}}
                if isinstance(face_data, dict) and "frames" in face_data:
                    frames_processed = len(face_data["frames"])
                    faces_detected = 1 if frames_processed > 0 else 0
                elif isinstance(face_data, list):
                    frames_processed = len(face_data)
                    faces_detected = 1 if frames_processed > 0 else 0

        # 4. TẠO CONFIG CHO VENDOR (Ép dùng Face Cache để tiết kiệm VRAM detect)
        config_data = {
            f"task_{job_id}": {
                "video_path": os.path.abspath(args.video),
                "audio_path": os.path.abspath(args.audio),
                "bbox_shift": 0,
                "bbox_path": os.path.abspath(args.face_json), # Truyền đường dẫn Cache
                "face_size": args.face_size,
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding="utf-8") as tmp_cfg:
            json.dump(config_data, tmp_cfg)
            tmp_cfg_path = tmp_cfg.name

        cmd = [
            sys.executable, inference_script,
            "--inference_config", tmp_cfg_path,
            "--result_dir", job_result_dir,
            "--batch_size", str(args.batch_size)
        ]
        
        if args.fp16:
            cmd.append("--use_float16")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = vendor_path
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        
        # Ép Device bằng biến môi trường (cô lập an toàn nhất)
        if actual_device == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = "-1"
        
        # 5. THỰC THI INFERENCE
        process = subprocess.run(cmd, cwd=vendor_path, env=env, capture_output=True, text=True, encoding="utf-8")
        
        if process.returncode != 0:
            raise RuntimeError(f"MuseTalk Worker Crash:\n{process.stderr}\n{process.stdout}")
            
        # 6. TRÍCH XUẤT OUTPUT CHÍNH XÁC THEO JOB
        list_of_files = glob.glob(os.path.join(job_result_dir, "**", "*.mp4"), recursive=True)
        if not list_of_files:
            raise RuntimeError(f"Không sinh ra MP4 trong {job_result_dir}.\nLog:\n{process.stderr}")
            
        shutil.move(list_of_files[0], args.output)
        
        # Tạm ước tính duration qua FPS 25
        duration = frames_processed / 25.0 if frames_processed > 0 else 0.0
        
        result = {
            "output_path": args.output,
            "duration": round(duration, 2), 
            "frames_processed": frames_processed, 
            "faces_detected": faces_detected
        }
        
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
        
    finally:
        # 7. CLEANUP BẢO VỆ (Bắt buộc chạy dù thành công hay crash)
        if tmp_cfg_path and os.path.exists(tmp_cfg_path):
            try: os.remove(tmp_cfg_path)
            except: pass
        if os.path.exists(job_result_dir):
            shutil.rmtree(job_result_dir, ignore_errors=True)

if __name__ == "__main__":
    main()