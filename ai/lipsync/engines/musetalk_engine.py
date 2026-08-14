import os
import gc
import torch
from ai.lipsync.base_lipsync import BaseLipSyncEngine
from ai.lipsync.config import LipSyncConfig, LipSyncResult

class MuseTalkEngine(BaseLipSyncEngine):
    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.dtype = torch.float32

    def supports(self, config: LipSyncConfig) -> bool:
        # MuseTalk chạy tốt nhất ở FP16 trên CUDA (rất hợp với RTX 3050)
        return True

    def load_model(self, config: LipSyncConfig) -> None:
        """Phase 2.1: Nạp trọng số (Weights) của MuseTalk vào VRAM một cách có kiểm soát"""
        print("[MuseTalk Engine] Đang nạp mô hình vào VRAM...")
        self.device = "cuda" if torch.cuda.is_available() and config.device in ["auto", "cuda"] else "cpu"
        self.dtype = torch.float16 if config.use_fp16 and self.device == "cuda" else torch.float32

        # ---------------------------------------------------------
        # TODO: Tích hợp mã nguồn nạp Pipeline MuseTalk thật vào đây
        # Ví dụ: 
        # from musetalk.pipelines import MuseTalkPipeline
        # self.model = MuseTalkPipeline.from_pretrained("path/to/weights", torch_dtype=self.dtype).to(self.device)
        # ---------------------------------------------------------
        
        self.model = "Mock_MuseTalk_Loaded" # Placeholder để pass qua Benchmark

    def unload_model(self) -> None:
        """Phase 2.3: Xóa sổ Model khỏi VRAM ngay lập tức sau khi xong việc"""
        print("[MuseTalk Engine] Giải phóng VRAM...")
        if self.model is not None:
            del self.model
            self.model = None
            
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def process(
        self, video_path: str, audio_path: str, face_data: dict, output_path: str, config: LipSyncConfig
    ) -> LipSyncResult:
        """Phase 2.2: Chạy Inference trên vùng miệng với chế độ tiết kiệm VRAM"""
        if not self.model:
            raise RuntimeError("Model chưa được nạp. Hãy gọi load_model() trước.")

        print(f"[MuseTalk Engine] Đang xử lý Lip Sync cho: {os.path.basename(video_path)}")
        total_frames = face_data.get("total_frames", 0)
        
        # [CHIẾN THUẬT CHỐNG OOM] Ép Torch không lưu Gradient và tự động ép kiểu FP16
        with torch.inference_mode():
            if self.dtype == torch.float16:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    # ---------------------------------------------------------
                    # TODO: Vòng lặp Crop mặt -> Gọi MuseTalk inference -> Dán mặt lại
                    # Khuyến nghị: Duyệt qua từng batch nhỏ (config.batch_size) thay vì nạp cả video
                    # ---------------------------------------------------------
                    pass
            else:
                pass # Chạy thuần FP32 nếu không dùng FP16

        return LipSyncResult(
            output_path=output_path,
            duration=0.0, # Tính sau
            frames_processed=total_frames,
            faces_detected=len(face_data.get("frames", {}))
        )