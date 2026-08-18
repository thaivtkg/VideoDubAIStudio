import os
import subprocess
import gc
import json
import sys

class LipSyncManager:
    def __init__(self):
        # [FIX REVIEW 1]: Lưu trữ tham chiếu tiến trình để có thể kill khi cần
        self.current_process = None 

    def process_lipsync(self, engine_name, video_path, audio_path, output_path, config):
        # ... (Phần chuẩn bị đường dẫn worker_script, kiểm tra file như cũ) ...
        worker_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai", "lipsync", "workers", f"{engine_name}_worker.py"))
        
        cmd = [
            sys.executable, worker_script,
            "--video", video_path,
            "--audio", audio_path,
            "--face_json", config.get("face_json", ""),
            "--output", output_path,
            "--device", config.get("device", "cuda"),
            "--batch_size", str(config.get("batch_size", 1))
        ]
        if config.get("fp16", False):
            cmd.append("--fp16")

        try:
            # Dùng Popen thay vì run() để không bị block hoàn toàn, giữ được tham chiếu
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Đợi tiến trình hoàn tất
            stdout, stderr = self.current_process.communicate()
            
            if self.current_process.returncode != 0:
                # Nếu bị kill chủ động (returncode thường là 1, -9, hoặc 15), ta không báo lỗi mà chỉ return
                raise RuntimeError(f"Worker Error: {stderr}\n{stdout}")
                
            # Phân tích kết quả JSON
            for line in reversed(stdout.strip().split('\n')):
                if line.startswith('{') and line.endswith('}'):
                    return json.loads(line)
                    
            return {"status": "success", "output_path": output_path}
            
        finally:
            # [BẢO VỆ TÀI NGUYÊN]: Luôn gỡ tham chiếu và dọn dẹp RAM Python
            self.current_process = None
            gc.collect()

    def cancel_process(self):
        """[FIX REVIEW 1]: Hàm tiêu diệt Zombie Process, kích hoạt khi tắt App hoặc bấm Hủy"""
        if self.current_process and self.current_process.poll() is None:
            try:
                if os.name == 'nt':
                    # Dùng taskkill với cờ /T (Tree) để giết cả luồng CUDA con ngầm
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)],
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    self.current_process.kill()
                print("[LipSyncManager] Đã tiêu diệt an toàn tiến trình Worker đang chạy ngầm.")
            except Exception as e:
                print(f"[LipSyncManager] Lỗi khi kill tiến trình: {e}")