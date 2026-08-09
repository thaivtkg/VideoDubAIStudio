import hashlib
from dataclasses import dataclass


@dataclass
class SubtitleItem:
    id: int
    start_time: float
    end_time: float
    text: str

    # TTS Settings
    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    emotion: str = "Natural"

    # Generated audio info
    audio_path: str = ""
    audio_duration: float = 0.0

    # Generation status: "not_generated", "generating", "generated", "error"
    audio_status: str = "not_generated"
    audio_error: str = ""

    def get_hash(self) -> str:
        """Tạo mã băm MD5 dựa trên nội dung và cấu hình giọng đọc để quản lý Cache."""
        config_string = f"{self.text}_{self.voice_id}_{self.speed}_{self.pitch}_{self.volume}_{self.emotion}"
        return hashlib.md5(config_string.encode('utf-8')).hexdigest()


class SubtitleManager:
    def __init__(self):
        self._subtitles: list[SubtitleItem] = []

    def load_subtitles(self, subtitles: list[SubtitleItem]):
        self._subtitles = subtitles

    def get_all(self) -> list[SubtitleItem]:
        return self._subtitles

    def get(self, index: int) -> SubtitleItem | None:
        if 0 <= index < len(self._subtitles):
            return self._subtitles[index]
        return None

    def get_by_id(self, sub_id: int) -> SubtitleItem | None:
        for sub in self._subtitles:
            if sub.id == sub_id:
                return sub
        return None

    def update_voice_settings(self, index: int, voice_id: str, speed: float, pitch: float, volume: float, emotion: str):
        sub = self.get(index)
        if sub:
            sub.voice_id = voice_id
            sub.speed = speed
            sub.pitch = pitch
            sub.volume = volume
            sub.emotion = emotion
            # Đánh dấu cần generate lại nếu hash thay đổi (sẽ xử lý logic cache sau)

    def set_audio_status(self, index: int, status: str, path: str = "", duration: float = 0.0, error: str = ""):
        sub = self.get(index)
        if sub:
            sub.audio_status = status
            sub.audio_path = path
            sub.audio_duration = duration
            sub.audio_error = error

    def get_pending_items(self) -> list[SubtitleItem]:
        return [sub for sub in self._subtitles if sub.audio_status != "generated"]