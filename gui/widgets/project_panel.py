from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt


class ProjectPanelWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #252526; color: white;")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        self.lbl_title = QLabel("<b>Project Assets</b>")
        self.lbl_video = QLabel("- Video: None")
        self.lbl_srt = QLabel("- SRT: None")

        # Bật WordWrap để không bị tràn chữ nếu đường dẫn dài
        self.lbl_video.setWordWrap(True)
        self.lbl_srt.setWordWrap(True)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_video)
        layout.addWidget(self.lbl_srt)

    def update_video(self, path: str):
        filename = path.split('/')[-1] if path else "None"
        self.lbl_video.setText(f"- Video: {filename}")
        self.lbl_video.setToolTip(path)

    def update_srt(self, path: str):
        filename = path.split('/')[-1] if path else "None"
        self.lbl_srt.setText(f"- SRT: {filename}")
        self.lbl_srt.setToolTip(path)