from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFrame, QComboBox, QSlider, QHBoxLayout, QGroupBox
)
from PySide6.QtCore import Qt


class PropertiesPanelWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background-color: #252526; color: white; }
            QGroupBox { font-weight: bold; border: 1px solid #333; margin-top: 10px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
            QLineEdit, QTextEdit, QComboBox { background-color: #1E1E1E; border: 1px solid #333; color: white; padding: 4px; }
            QPushButton { background-color: #3E3E42; border: 1px solid #555; padding: 6px; }
            QPushButton:hover { background-color: #007ACC; }
            QPushButton:disabled { background-color: #2D2D30; color: #777; }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.current_index = -1

        self._setup_timing_group()
        self._setup_voice_group()
        self._setup_audio_group()

        # Nút Save nằm dưới cùng, tách biệt với Generate
        self.btn_save = QPushButton("Save Changes")
        self.layout.addWidget(self.btn_save)

    def _setup_timing_group(self):
        group = QGroupBox("SUBTITLE")
        lay = QVBoxLayout(group)

        # Cấu trúc ngang cho ID, Start, End để tiết kiệm không gian
        row1 = QHBoxLayout()
        self.txt_id = QLineEdit();
        self.txt_id.setReadOnly(True);
        self.txt_id.setMaximumWidth(50)
        self.txt_start = QLineEdit()
        self.txt_end = QLineEdit()

        row1.addWidget(QLabel("ID:"))
        row1.addWidget(self.txt_id)
        row1.addWidget(QLabel("Start:"))
        row1.addWidget(self.txt_start)
        row1.addWidget(QLabel("End:"))
        row1.addWidget(self.txt_end)
        lay.addLayout(row1)

        lay.addWidget(QLabel("Text:"))
        self.txt_text = QTextEdit()
        self.txt_text.setMaximumHeight(80)
        lay.addWidget(self.txt_text)

        self.layout.addWidget(group)

    def _setup_voice_group(self):
        group = QGroupBox("VOICE SETTINGS")
        lay = QVBoxLayout(group)

        # Voice Selection
        row_voice = QHBoxLayout()
        self.cbo_language = QComboBox()
        self.cbo_language.addItems(["Vietnamese", "English"])
        self.cbo_voice = QComboBox()
        self.cbo_voice.addItems(["Female 01", "Female 02", "Male 01"])
        row_voice.addWidget(self.cbo_language)
        row_voice.addWidget(self.cbo_voice)
        lay.addLayout(row_voice)

        # Speed Slider
        row_speed = QHBoxLayout()
        self.lbl_speed_val = QLabel("1.00x")
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setRange(75, 125)  # 0.75x đến 1.25x
        self.sld_speed.setValue(100)
        self.sld_speed.valueChanged.connect(lambda v: self.lbl_speed_val.setText(f"{v / 100:.2f}x"))
        row_speed.addWidget(QLabel("Speed:"))
        row_speed.addWidget(self.sld_speed)
        row_speed.addWidget(self.lbl_speed_val)
        lay.addLayout(row_speed)

        # Emotion
        row_emo = QHBoxLayout()
        self.cbo_emotion = QComboBox()
        self.cbo_emotion.addItems(["Natural", "Happy", "Sad", "Serious", "Excited"])
        row_emo.addWidget(QLabel("Emotion:"))
        row_emo.addWidget(self.cbo_emotion)
        lay.addLayout(row_emo)

        self.layout.addWidget(group)

    def _setup_audio_group(self):
        group = QGroupBox("AUDIO")
        lay = QVBoxLayout(group)

        self.lbl_audio_status = QLabel("Status: ○ Not Generated")
        self.lbl_audio_duration = QLabel("Duration: 0.00 s")
        lay.addWidget(self.lbl_audio_status)
        lay.addWidget(self.lbl_audio_duration)

        row_btns = QHBoxLayout()
        self.btn_preview = QPushButton("▶ Preview")
        self.btn_preview.setEnabled(False)  # Chỉ bật khi Status = Generated

        self.btn_generate = QPushButton("Generate Voice")
        row_btns.addWidget(self.btn_preview)
        row_btns.addWidget(self.btn_generate)
        lay.addLayout(row_btns)

        self.layout.addWidget(group)