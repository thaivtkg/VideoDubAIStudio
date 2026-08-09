from abc import ABC, abstractmethod


class BaseTTSEngine(ABC):

    @abstractmethod
    def get_engine_name(self) -> str:
        """Trả về tên của Engine (VD: 'VITS Offline', 'ChatTTS')."""
        pass

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """Trả về danh sách ngôn ngữ hỗ trợ."""
        pass

    @abstractmethod
    def get_voices(self, language: str) -> list[dict]:
        """Trả về danh sách giọng đọc của ngôn ngữ được chọn.
           Định dạng trả về: [{'id': 'female_01', 'name': 'Nữ 01', 'emotions': ['Natural', 'Happy']}]
        """
        pass

    @abstractmethod
    def load_model(self) -> bool:
        """Nạp model vào VRAM/RAM. Trả về True nếu nạp thành công."""
        pass

    @abstractmethod
    def unload_model(self):
        """Giải phóng VRAM/RAM."""
        pass

    @abstractmethod
    def generate(self, text: str, voice_id: str, speed: float, pitch: float, emotion: str, output_path: str) -> bool:
        """Thực thi tạo file audio WAV. Trả về True nếu thành công."""
        pass