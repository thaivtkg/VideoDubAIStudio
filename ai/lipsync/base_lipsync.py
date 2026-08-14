from abc import ABC, abstractmethod
from ai.tts.lipsync.config import LipSyncConfig, LipSyncResult

class BaseLipSyncEngine(ABC):

    @abstractmethod
    def load_model(self, config: LipSyncConfig) -> None:
        """Nạp mô hình Lip Sync vào bộ nhớ (RAM/VRAM) dựa trên cấu hình."""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Giải phóng hoàn toàn mô hình khỏi bộ nhớ để tránh OOM."""
        pass

    @abstractmethod
    def process(
        self,
        video_path: str,
        audio_path: str,
        face_data: dict,
        output_path: str,
        config: LipSyncConfig,
    ) -> LipSyncResult:
        """
        Thực thi ghép khẩu hình (Lip Sync).
        Nhận vào video gốc, audio dubbing (WAV tổng), và dữ liệu cache khuôn mặt.
        Trả về kết quả chứa đường dẫn video thành phẩm và các metrics.
        """
        pass

    @abstractmethod
    def supports(self, config: LipSyncConfig) -> bool:
        """Kiểm tra xem Engine có hỗ trợ cấu hình hiện tại (ví dụ FP16 trên thiết bị cũ) hay không."""
        pass