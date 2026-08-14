import gc
import torch
from core.face_manager import FaceManager
from ai.lipsync.engines.musetalk_engine import MuseTalkEngine
from ai.lipsync.config import LipSyncConfig

class LipSyncManager:
    def __init__(self):
        self.face_manager = FaceManager()
        # Khởi tạo các Engine (Chỉ lưu instance, KHÔNG NẠP MODEL ở bước này)
        self.engines = {
            "musetalk": MuseTalkEngine(),
            # "wav2lip": Wav2LipEngine() # Mở khóa khi có S4.5
        }

    def _clean_gpu_memory(self):
        """Công cụ dọn rác bắt buộc giữa các Phase"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def process_lipsync(self, engine_name: str, video_path: str, audio_path: str, output_path: str, config: LipSyncConfig):
        """Chu trình 3 Phase chuẩn mực để bảo vệ hệ thống 4GB VRAM"""
        
        if engine_name not in self.engines:
            raise ValueError(f"Engine {engine_name} không tồn tại.")
        engine = self.engines[engine_name]

        # ==========================================
        # PHASE 1: NHẬN DIỆN VÀ CACHE KHUÔN MẶT
        # ==========================================
        print("\n--- [PHASE 1] DETECTING FACES ---")
        face_data = self.face_manager.process_and_cache(video_path)
        
        # Bắt buộc dọn rác hệ thống sau khi Detector (MediaPipe) nhả RAM
        self._clean_gpu_memory()

        # ==========================================
        # PHASE 2: LIP SYNC MODEL (AI INFERENCE)
        # ==========================================
        print("\n--- [PHASE 2] RUNNING LIP SYNC MODEL ---")
        try:
            engine.load_model(config)
            result = engine.process(video_path, audio_path, face_data, output_path, config)
        finally:
            # PHASE 3: LUÔN GIẢI PHÓNG VRAM DÙ CÓ LỖI HAY KHÔNG (Rule 59)
            print("\n--- [PHASE 3] CLEANUP & UNLOAD ---")
            engine.unload_model()
            self._clean_gpu_memory()
            
        return result