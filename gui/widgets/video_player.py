from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QSlider
from PySide6.QtCore import Qt, QUrl


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
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.controls_layout = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_pause = QPushButton("Pause")

        # THAY ĐỔI: Sử dụng ClickableSlider thay cho QSlider mặc định
        self.slider = ClickableSlider(Qt.Horizontal)

        self.controls_layout.addWidget(self.btn_play)
        self.controls_layout.addWidget(self.btn_pause)
        self.controls_layout.addWidget(self.slider)

        self.layout.addWidget(self.video_widget)
        self.layout.addLayout(self.controls_layout)

        self.btn_play.clicked.connect(self.player.play)
        self.btn_pause.clicked.connect(self.player.pause)
        self.player.positionChanged.connect(self.slider.setValue)
        self.player.durationChanged.connect(self.slider.setMaximum)
        self.slider.sliderMoved.connect(self.player.setPosition)

    def load_video(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))