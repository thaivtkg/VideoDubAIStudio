from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QRectF

class AudioTimelineWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(120)
        self.video_duration = 0     # mili-giây
        self.current_position = 0   # mili-giây
        self.subtitles = []         # Danh sách SubtitleItem
        
        # Cấu hình màu sắc
        self.bg_color = QColor("#1E1E1E")
        self.sub_color = QColor("#007ACC")      # Màu khối phụ đề
        self.audio_color = QColor("#4CAF50")    # Màu khối audio đã sinh
        self.playhead_color = QColor("#FF5252") # Kim chỉ thời gian (đỏ)
        
    def set_duration(self, duration_ms):
        self.video_duration = duration_ms
        self.update()

    def set_position(self, position_ms):
        self.current_position = position_ms
        self.update()

    def update_data(self, subtitles):
        self.subtitles = subtitles
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Vẽ nền
        rect = self.rect()
        painter.fillRect(rect, self.bg_color)
        
        if self.video_duration <= 0:
            return

        width = rect.width()
        px_per_ms = width / self.video_duration
        
        # Định nghĩa các Track
        track_sub_y = 30
        track_sub_h = 25
        track_audio_y = 65
        track_audio_h = 25

        # Vẽ đường phân cách
        painter.setPen(QPen(QColor("#333"), 1))
        painter.drawLine(0, track_audio_y - 5, width, track_audio_y - 5)

        # 2. Vẽ các Clip
        for sub in self.subtitles:
            start_x = sub.start_time * 1000 * px_per_ms
            
            # Vẽ khối Phụ đề (Target)
            sub_w = (sub.end_time - sub.start_time) * 1000 * px_per_ms
            painter.setBrush(QBrush(self.sub_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(start_x, track_sub_y, sub_w, track_sub_h))
            
            # Vẽ khối Audio (Thực tế)
            if sub.audio_status == "generated" and sub.audio_duration > 0:
                audio_w = sub.audio_duration * 1000 * px_per_ms
                
                # Cảnh báo nếu Audio dài hơn Subtitle (Overlap nguy hiểm)
                if sub.audio_duration > (sub.end_time - sub.start_time):
                    painter.setBrush(QBrush(QColor("#FF9800"))) # Cam cảnh báo
                else:
                    painter.setBrush(QBrush(self.audio_color))
                    
                painter.drawRect(QRectF(start_x, track_audio_y, audio_w, track_audio_h))
                
                # Vẽ ID text lên Audio block để dễ nhận diện
                painter.setPen(QColor("white"))
                painter.drawText(QRectF(start_x + 5, track_audio_y, audio_w, track_audio_h), Qt.AlignVCenter | Qt.AlignLeft, f"#{sub.id}")

        # 3. Vẽ Kim thời gian (Playhead)
        playhead_x = int(self.current_position * px_per_ms) 
        painter.setPen(QPen(self.playhead_color, 2))
        painter.drawLine(playhead_x, 0, playhead_x, rect.height())