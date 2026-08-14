from dataclasses import dataclass
from typing import Dict, List
from core.subtitle_manager import SubtitleItem

@dataclass
class AudioClip:
    subtitle_id: int
    audio_path: str
    start_time: float      # Timestamp bắt đầu trên timeline video (giây)
    duration: float        # Thời lượng thực tế của file audio (giây)

class TimelineManager:
    def __init__(self):
        self.clips: Dict[int, AudioClip] = {}

    def sync_from_subtitles(self, subtitles: List[SubtitleItem]):
        """Đồng bộ dữ liệu: Chỉ lấy những subtitle đã được generate Audio"""
        current_ids = set()
        for sub in subtitles:
            if sub.audio_status == "generated" and sub.audio_path:
                current_ids.add(sub.id)
                self.clips[sub.id] = AudioClip(
                    subtitle_id=sub.id,
                    audio_path=sub.audio_path,
                    start_time=sub.start_time,
                    duration=sub.audio_duration
                )
        
        # Xóa các clip thuộc về subtitle đã bị invalidate cache (Not Generated)
        keys_to_remove = [k for k in self.clips.keys() if k not in current_ids]
        for k in keys_to_remove:
            del self.clips[k]

    def get_clips_in_range(self, current_time: float) -> List[AudioClip]:
        """Trả về danh sách các Audio Clip cần được phát tại mốc thời gian hiện tại"""
        active_clips = []
        for clip in self.clips.values():
            # Nếu current_time nằm trong khoảng [start, start + duration] của clip
            if clip.start_time <= current_time <= (clip.start_time + clip.duration):
                active_clips.append(clip)
        return active_clips