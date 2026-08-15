import argparse
import json
import sys
import os
import subprocess
import shutil
import glob
import tempfile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--face_json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()

    vendor_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../vendor/MuseTalk"))
    inference_script = os.path.join(vendor_path, "scripts", "inference.py")
    results_dir = os.path.join(vendor_path, "results")
    
    try:
        config_data = {
            "task_1": {
                "video_path": os.path.abspath(args.video),
                "audio_path": os.path.abspath(args.audio),
                "bbox_shift": 0
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_cfg:
            json.dump(config_data, tmp_cfg)
            tmp_cfg_path = tmp_cfg.name

        cmd = [
            sys.executable, inference_script,
            "--inference_config", tmp_cfg_path,
            "--result_dir", results_dir,
            "--batch_size", str(args.batch_size)
        ]
        
        if args.fp16:
            cmd.append("--use_float16")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = vendor_path
        
        # BẮT BUỘC SỬ DỤNG UTF-8 TRÊN WINDOWS
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        
        # Thêm cờ encoding="utf-8" để subprocess không bị crash khi gặp tiếng Nhật/Unicode
        process = subprocess.run(cmd, cwd=vendor_path, env=env, capture_output=True, text=True, encoding="utf-8")
        
        if os.path.exists(tmp_cfg_path):
            os.remove(tmp_cfg_path)

        if process.returncode != 0:
            raise RuntimeError(f"MuseTalk Core Error:\n{process.stderr}\n{process.stdout}")
            
        list_of_files = glob.glob(os.path.join(results_dir, "**", "*.mp4"), recursive=True)
        if not list_of_files:
            debug_log = (
                "KHÔNG TÌM THẤY VIDEO THÀNH PHẨM. CHI TIẾT LỖI TỪ MUSETALK:\n\n"
                f"--- OUTPUT TRÊN MÀN HÌNH (STDOUT) ---\n{process.stdout}\n\n"
                f"--- LỖI HỆ THỐNG (STDERR) ---\n{process.stderr}"
            )
            raise RuntimeError(debug_log)
            
        latest_file = max(list_of_files, key=os.path.getctime)
        shutil.move(latest_file, args.output)
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
        
    result = {
        "output_path": args.output,
        "duration": 0.0, 
        "frames_processed": -1, 
        "faces_detected": 1
    }
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()