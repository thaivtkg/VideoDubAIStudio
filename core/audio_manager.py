import os

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioManager(QObject):
    def __init__(self, pool_size=3):
        super().__init__()
        self.pool_size = pool_size
        self.players = []
        self.outputs = []
        self.last_sync_time = 0  # [MỚI] Dùng để detect hành vi Seek
        
        for _ in range(self.pool_size):
            audio_output = QAudioOutput()
            player = QMediaPlayer()
            player.setAudioOutput(audio_output)
            self.players.append(player)
            self.outputs.append(audio_output)
            
        self.active_clips = {} 

    def tick(self, current_time_ms: int, active_clips: list, is_seeking: bool = False):
        current_time_sec = current_time_ms / 1000.0
        active_ids = {clip.subtitle_id for clip in active_clips}
        
        # Kết hợp cờ is_seeking với heuristic 300ms cũ
        if is_seeking or abs(current_time_ms - self.last_sync_time) > 300:
            self.stop_all()
            self.active_clips.clear()
            
        self.last_sync_time = current_time_ms
        
        # 1. Dừng các audio không còn active
        for sub_id, player_idx in list(self.active_clips.items()):
            if sub_id not in active_ids:
                self.players[player_idx].stop()
                self.players[player_idx].setSource(QUrl())
                del self.active_clips[sub_id]

        # 2. Kích hoạt/Re-sync các audio
        for clip in active_clips:
            if clip.subtitle_id not in self.active_clips:
                free_idx = self._get_free_player_index()
                if free_idx is not None and os.path.exists(clip.audio_path):
                    player = self.players[free_idx]
                    
                    # [SỬA TẠI ĐÂY] Gọi hàm an toàn thay vì gán trực tiếp
                    offset_sec = current_time_sec - clip.start_time
                    offset_ms = int(offset_sec * 1000) if offset_sec > 0 else 0
                    self.play_clip_safely(player, clip.audio_path, offset_ms)
                    
                    self.active_clips[clip.subtitle_id] = free_idx

    def _get_free_player_index(self):
        """Tìm một player đang rảnh trong Pool"""
        for i, player in enumerate(self.players):
            if player.playbackState() == QMediaPlayer.StoppedState:
                return i
        return None

    def stop_all(self):
        """Dừng toàn bộ âm thanh (Dùng khi người dùng Pause Video)"""
        for player in self.players:
            player.stop()
            player.setSource(QUrl())
        self.active_clips.clear()

    def play_clip_safely(self, player, clip_path, offset_ms):
        """Đảm bảo Backend nạp xong Media trước khi tua và phát (có bắt lỗi an toàn)"""
        def on_status_changed(status):
            if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
                if offset_ms > 0:
                    player.setPosition(offset_ms)
                player.play()
                player.mediaStatusChanged.disconnect(on_status_changed)
                
            # [PHÒNG THỦ] Tránh rò rỉ Signal nếu file bị hỏng hoặc backend từ chối nạp
            elif status == QMediaPlayer.MediaStatus.InvalidMedia:
                player.mediaStatusChanged.disconnect(on_status_changed)

        player.mediaStatusChanged.connect(on_status_changed)
        player.setSource(QUrl.fromLocalFile(clip_path))