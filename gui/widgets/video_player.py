from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


# Thêm class Custom Slider ngay phía trên class VideoPlayerWidget
class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Tính toán phần trăm vị trí click chuột để gán Value
            val = (event.position().x() / self.width()) * (self.maximum() - self.minimum()) + self.minimum()
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))  # Kích hoạt tín hiệu tua video
        super().mousePressEvent(event)


class VideoPlayerWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.layout.addWidget(self.video_widget)
        
        # --- KHU VỰC ĐIỀU KHIỂN (CONTROLS) ---
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 1. Nút Play/Pause Toggle
        self.btn_toggle = QPushButton()
        self.btn_toggle.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_toggle.setFixedWidth(40)
        self.btn_toggle.clicked.connect(self.toggle_playback)
        
        # 2. Thanh trượt
        self.slider = ClickableSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
        
        # 3. Label Thời gian
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFixedWidth(110)
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_time.setStyleSheet("color: white; font-size: 12px;")
        
        control_layout.addWidget(self.btn_toggle)
        control_layout.addWidget(self.slider)
        control_layout.addWidget(self.lbl_time)
        
        self.layout.addLayout(control_layout)
        self.layout.setStretch(0, 1)
        
        # --- KẾT NỐI TÍN HIỆU ---
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.state_changed)

    def load_video(self, file_path):
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.pause() # Nạp xong thì Pause chứ không Play ngay

    def toggle_playback(self):
        """Xử lý nút Toggle Play/Pause"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def state_changed(self, state):
        """Đổi Icon nút khi trạng thái Player thay đổi"""
        if state == QMediaPlayer.PlayingState:
            self.btn_toggle.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.btn_toggle.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def position_changed(self, position):
        self.slider.setValue(position)
        self.update_time_label()

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self.update_time_label()

    def set_position(self, position):
        self.player.setPosition(position)

    def update_time_label(self):
        """Định dạng và hiển thị thời gian MM:SS hoặc HH:MM:SS"""
        pos_sec = self.player.position() // 1000
        dur_sec = self.player.duration() // 1000

        def format_time(seconds):
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h > 0:
                return f"{h:02d}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"

        self.lbl_time.setText(f"{format_time(pos_sec)} / {format_time(dur_sec)}")