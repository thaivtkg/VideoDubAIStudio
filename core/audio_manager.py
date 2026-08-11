import os
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QObject, QUrl

class AudioManager(QObject):
    def __init__(self, pool_size=3):
        super().__init__()
        self.pool_size = pool_size
        self.players = []
        self.outputs = []
        
        # Khởi tạo Pool để hỗ trợ phát đè nhiều âm thanh (Overlap) và tránh trễ I/O
        for _ in range(self.pool_size):
            audio_output = QAudioOutput()
            player = QMediaPlayer()
            player.setAudioOutput(audio_output)
            self.players.append(player)
            self.outputs.append(audio_output)
            
        self.active_clips = {} # Mapping: subtitle_id -> player_index

    def tick(self, current_time_ms: int, active_clips: list):
        """Được gọi liên tục từ VideoPlayer để đồng bộ hóa âm thanh"""
        current_time_sec = current_time_ms / 1000.0
        active_ids = {clip.subtitle_id for clip in active_clips}
        
        # 1. Dừng và nhả file các audio đã vượt quá thời gian phát (End of Clip)
        for sub_id, player_idx in list(self.active_clips.items()):
            if sub_id not in active_ids:
                self.players[player_idx].stop()
                self.players[player_idx].setSource(QUrl())
                del self.active_clips[sub_id]

        # 2. Kích hoạt phát các audio mới đi vào mốc thời gian
        for clip in active_clips:
            if clip.subtitle_id not in self.active_clips:
                free_idx = self._get_free_player_index()
                if free_idx is not None and os.path.exists(clip.audio_path):
                    player = self.players[free_idx]
                    player.setSource(QUrl.fromLocalFile(clip.audio_path))
                    
                    # CỰC KỲ QUAN TRỌNG: Tính toán Offset
                    # Nếu người dùng click tua video vào giữa đoạn audio, phải tua audio đi tương ứng
                    offset_sec = current_time_sec - clip.start_time
                    if offset_sec > 0:
                        player.setPosition(int(offset_sec * 1000))
                        
                    player.play()
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