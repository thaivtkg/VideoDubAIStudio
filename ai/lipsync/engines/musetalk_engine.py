import os
import json
import subprocess
import tempfile
import sys
from ai.lipsync.base_lipsync import BaseLipSyncEngine
from ai.lipsync.config import LipSyncConfig, LipSyncResult

class MuseTalkEngine(BaseLipSyncEngine):
    def __init__(self):
        self.worker_script = "ai/lipsync/workers/musetalk_worker.py"

    def supports(self, config: LipSyncConfig) -> bool:
        return True

    def load_model(self, config: LipSyncConfig) -> None:
        """Adapter không giữ Model trên RAM, nên hàm này không làm gì cả (No-op)"""
        pass

    def unload_model(self) -> None:
        """OS sẽ tự thu hồi VRAM khi Subprocess tắt, Adapter không cần can thiệp"""
        pass

    def process(
        self, video_path: str, audio_path: str, face_data: dict, output_path: str, config: LipSyncConfig
    ) -> LipSyncResult:
        """Tạo Subprocess độc lập để chạy MuseTalk"""
        print(f"[MuseTalk Adapter] Chuẩn bị khởi chạy Worker cho: {os.path.basename(video_path)}")
        
        # 1. Ghi face_data ra file tạm để truyền cho Subprocess
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_face:
            json.dump(face_data, tmp_face)
            tmp_face_path = tmp_face.name

        try:
            # 2. Xây dựng lệnh gọi Worker
            command = [
                sys.executable, self.worker_script,
                "--video", video_path,
                "--audio", audio_path,
                "--face_json", tmp_face_path,
                "--output", output_path,
                "--device", config.device,
                "--batch_size", str(config.batch_size)
            ]
            
            if config.use_fp16:
                command.append("--fp16")

            # 3. Khởi chạy và chờ kết quả
            print(f"[MuseTalk Adapter] Đang chạy AI Inference trong tiến trình cô lập...")
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            
            # Đọc log từ Worker (Dòng cuối cùng phải là JSON Result)
            lines = process.stdout.strip().split('\n')
            result_data = json.loads(lines[-1])
            
            print(f"[MuseTalk Adapter] Worker hoàn tất. VRAM đã được hệ thống thu hồi.")
            
            return LipSyncResult(
                output_path=result_data["output_path"],
                duration=result_data["duration"],
                frames_processed=result_data["frames_processed"],
                faces_detected=result_data["faces_detected"]
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Lỗi khi chạy MuseTalk Worker: {e.stderr}\n{e.stdout}")
        except json.JSONDecodeError:
            raise RuntimeError(f"Worker trả về dữ liệu không hợp lệ. Output: {process.stdout}")
        finally:
            # Dọn dẹp file tạm
            if os.path.exists(tmp_face_path):
                os.remove(tmp_face_path)