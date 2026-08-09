import json
import os

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMenu,  # noqa: F401
    QProgressDialog,
    QTextEdit,  # noqa: F401
    QVBoxLayout,
    QWidget,  # noqa: F401
)

from ai.tts.engines.mock_tts import MockTTSEngine
from core.project_manager import ProjectManager
from core.srt_parser import parse_srt
from core.subtitle_manager import SubtitleManager
from gui.widgets.project_panel import ProjectPanelWidget
from gui.widgets.properties_panel import PropertiesPanelWidget
from gui.widgets.subtitle_table import SubtitleTableWidget
from gui.widgets.video_player import VideoPlayerWidget
from workers.tts_worker import TTSTask, TTSWorker


class PlaceholderWidget(QFrame):
    """Widget tạm thời để giữ chỗ trong Sprint 1"""
    def __init__(self, title, color):
        super().__init__()
        # Cài đặt Theme cơ bản (Dark Mode)
        # self.setStyleSheet("""
        #             QMainWindow { background-color: #1E1E1E; color: white; }
        #             QMenuBar { background-color: #1E1E1E; color: white; }
        #             QMenuBar::item { background-color: transparent; padding: 4px 10px; }
        #             QMenuBar::item:selected { background-color: #3E3E42; }
        #             QMenu { background-color: #252526; color: white; border: 1px solid #333; }
        #             QMenu::item { padding: 5px 20px 5px 20px; }
        #             QMenu::item:selected { background-color: #007ACC; }
        #         """)
        layout = QVBoxLayout()
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(label)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Dubbing Studio v0.1")
        self.resize(1280, 720)
        self.setMinimumSize(1280, 720)

        # Cài đặt Theme cơ bản (Dark Mode)
        self.setStyleSheet("QMainWindow { background-color: #1E1E1E; color: white; }")

        # Trình phát độc lập cho Preview Voice
        self.preview_audio = QAudioOutput()
        self.preview_player = QMediaPlayer()
        self.preview_player.setAudioOutput(self.preview_audio)

        self._setup_menu()
        self._setup_ui()
        self.statusBar().showMessage("Ready")
        # Khởi tạo Quản lý Dự án
        self.project_manager = ProjectManager()
        self.project_manager.new_project("Untitled")
        # Quản lý dữ liệu và AI Engine
        self.subtitle_manager = SubtitleManager()
        self.tts_engine = MockTTSEngine()
        self.tts_worker = None


    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Project")
        file_menu.addAction("Open Project...", self.action_open_project)
        file_menu.addAction("Save Project", self.action_save_project)
        file_menu.addSeparator()

        # Thêm 2 action mới để Import
        file_menu.addAction("Import Video...", self.action_import_video)
        file_menu.addAction("Import Subtitle...", self.action_import_subtitle)

        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        voice_menu = menubar.addMenu("Voice")
        voice_menu.addAction("Generate All Pending", self.action_generate_all_pending)

    def _setup_ui(self):
        # 1. Center: Video Player
        self.video_player = VideoPlayerWidget()
        self.setCentralWidget(self.video_player)

        # 2. Left Dock: Project Panel
        dock_project = QDockWidget("Project Panel", self)
        self.project_panel = ProjectPanelWidget()
        dock_project.setWidget(self.project_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_project)

        # 3. Right Dock: Properties
        dock_properties = QDockWidget("Properties", self)
        self.properties_panel = PropertiesPanelWidget()
        dock_properties.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_properties)

        # 4. Bottom Dock: Subtitle Table
        dock_timeline = QDockWidget("Subtitle Timeline", self)
        self.subtitle_table = SubtitleTableWidget()
        dock_timeline.setWidget(self.subtitle_table)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_timeline)

        # 5. Kết nối sự kiện (Signals / Slots)
        self.subtitle_table.selectionModel().selectionChanged.connect(self.on_subtitle_selected)
        self.properties_panel.btn_save.clicked.connect(self.save_subtitle_changes)
        self.properties_panel.btn_generate.clicked.connect(self.generate_single_voice)
        self.properties_panel.btn_preview.clicked.connect(self.toggle_preview_voice)
        self.preview_player.playbackStateChanged.connect(self.on_preview_state_changed)

        # THÊM LOGIC AUTO-SAVE TẠI ĐÂY
        # Bắt sự kiện khi người dùng thay đổi Voice, Speed hoặc Emotion
        self.properties_panel.cbo_voice.currentIndexChanged.connect(self.auto_save_settings)
        self.properties_panel.cbo_emotion.currentIndexChanged.connect(self.auto_save_settings)
        # Sử dụng sliderReleased thay vì valueChanged để tránh việc save liên tục hàng chục lần khi người dùng đang kéo chuột
        self.properties_panel.sld_speed.sliderReleased.connect(self.auto_save_settings)
        
        # Kết nối sự kiện mất focus (người dùng gõ xong chữ rồi click ra ngoài) cho trường Text
        self.properties_panel.txt_text.installEventFilter(self)

    def action_import_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Video", "",
                                                   "Video Files (*.mp4 *.mkv *.mov *.avi);;All Files (*)")
        if file_path:
            self.video_player.load_video(file_path)
            self.project_panel.update_video(file_path)
            # Lưu đường dẫn vào Project Data
            self.project_manager.current_project.video_path = file_path
            self.statusBar().showMessage(f"Đã tải Video: {file_path}")

    def action_import_subtitle(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Phụ đề", "",
                                                   "Subtitle Files (*.srt);;All Files (*)")
        if file_path:
            subtitles_data = parse_srt(file_path)
            if subtitles_data:
                # Nạp dữ liệu vào SubtitleManager
                self.subtitle_manager.load_subtitles(subtitles_data)

                # Cập nhật Table và Panel
                self.subtitle_table.model.update_data(self.subtitle_manager.get_all())
                self.project_panel.update_srt(file_path)

                self.project_manager.current_project.srt_path = file_path
                self.project_manager.current_project.subtitles = subtitles_data

                self.statusBar().showMessage(f"Đã tải {len(subtitles_data)} dòng phụ đề.")
            else:
                self.statusBar().showMessage("Lỗi: Không thể đọc file SRT hoặc file rỗng.", 5000)

    def on_subtitle_selected(self, selected, deselected):
        indexes = self.subtitle_table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            sub_item = self.subtitle_manager.get(row)
            if not sub_item:
                return

            # Đổ dữ liệu cơ bản
            self.properties_panel.current_index = row
            self.properties_panel.txt_id.setText(str(sub_item.id))
            self.properties_panel.txt_start.setText(f"{sub_item.start_time:.3f}")
            self.properties_panel.txt_end.setText(f"{sub_item.end_time:.3f}")
            self.properties_panel.txt_text.setPlainText(sub_item.text)

            # Đổ dữ liệu TTS
            self.properties_panel.cbo_voice.setCurrentText(
                sub_item.voice_id if sub_item.voice_id != "default" else "Female 01")
            self.properties_panel.sld_speed.setValue(int(sub_item.speed * 100))
            self.properties_panel.cbo_emotion.setCurrentText(sub_item.emotion)

            # Đổ dữ liệu Trạng thái Audio
            if sub_item.audio_status == "generated":
                self.properties_panel.lbl_audio_status.setText("Status: ✓ Generated")
                self.properties_panel.lbl_audio_duration.setText(f"Duration: {sub_item.audio_duration:.2f} s")
                self.properties_panel.btn_preview.setEnabled(True)
            elif sub_item.audio_status == "error":
                self.properties_panel.lbl_audio_status.setText("Status: ⚠ Error")
                self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                self.properties_panel.btn_preview.setEnabled(False)
            else:
                self.properties_panel.lbl_audio_status.setText("Status: ○ Not Generated")
                self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                self.properties_panel.btn_preview.setEnabled(False)

            # Seek video an toàn
            video_duration = self.video_player.player.duration()
            if video_duration > 0:
                target_position = int(sub_item.start_time * 1000)
                if target_position <= video_duration:
                    self.video_player.player.setPosition(target_position)

    def save_subtitle_changes(self):
        """Kích hoạt khi bấm nút Save Changes trên Properties Panel"""
        row = self.properties_panel.current_index
        if row >= 0:
            try:
                # Lấy dữ liệu Text/Time mới
                new_start = float(self.properties_panel.txt_start.text())
                new_end = float(self.properties_panel.txt_end.text())
                new_text = self.properties_panel.txt_text.toPlainText()

                # Lấy cấu hình TTS mới
                new_voice = self.properties_panel.cbo_voice.currentText()
                new_speed = self.properties_panel.sld_speed.value() / 100.0
                new_emotion = self.properties_panel.cbo_emotion.currentText()

                sub_item = self.subtitle_manager.get(row)
                old_hash = sub_item.get_hash()

                # Cập nhật Data Object
                sub_item.start_time = new_start
                sub_item.end_time = new_end
                sub_item.text = new_text
                sub_item.voice_id = new_voice
                sub_item.speed = new_speed
                sub_item.emotion = new_emotion

                new_hash = sub_item.get_hash()

                # XỬ LÝ CACHE: Nếu hash thay đổi (do Text hoặc Cấu hình Voice thay đổi)
                if old_hash != new_hash:
                    sub_item.audio_status = "not_generated"
                    sub_item.audio_path = ""
                    sub_item.audio_duration = 0.0

                    # Reset UI Properties
                    self.properties_panel.lbl_audio_status.setText("Status: ○ Not Generated")
                    self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                    self.properties_panel.btn_preview.setEnabled(False)
                    self.statusBar().showMessage("Cấu hình thay đổi, yêu cầu Generate lại Audio.", 5000)
                else:
                    self.statusBar().showMessage(f"Đã cập nhật dòng ID: {sub_item.id}")

                # Cập nhật TableView
                top_left = self.subtitle_table.model.index(row, 1)
                bottom_right = self.subtitle_table.model.index(row, 3)
                self.subtitle_table.model.dataChanged.emit(top_left, bottom_right)

            except ValueError:
                self.statusBar().showMessage("Lỗi: Start/End phải là số hợp lệ!", 5000)

    def action_save_project(self):
        """Mở hộp thoại lưu project và xuất ra file JSON (.vds)"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu Project", "", "Video Dubbing Studio (*.vds)")
        if file_path:
            # Lấy toàn bộ dữ liệu (gồm cả cấu hình TTS) từ Manager
            self.project_manager.current_project.subtitles = self.subtitle_manager.get_all()

            if self.project_manager.save_project(file_path):
                self.statusBar().showMessage(f"Đã lưu project tại: {file_path}", 5000)
                self.setWindowTitle(f"Video Dubbing Studio v0.1 - {file_path}")
            else:
                self.statusBar().showMessage("Lỗi: Không thể lưu project!", 5000)

    def action_open_project(self):
        """Mở file .vds và khôi phục trạng thái làm việc"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Mở Project", "", "Video Dubbing Studio (*.vds)")
        if file_path:
            if self.project_manager.load_project(file_path):
                proj = self.project_manager.current_project

                if proj.video_path:
                    self.video_player.load_video(proj.video_path)
                    self.project_panel.update_video(proj.video_path)

                if proj.subtitles:
                    # Nạp ngược lại vào Manager và Table
                    self.subtitle_manager.load_subtitles(proj.subtitles)
                    self.subtitle_table.model.update_data(self.subtitle_manager.get_all())

                if proj.srt_path:
                    self.project_panel.update_srt(proj.srt_path)

                self.statusBar().showMessage(f"Đã mở project: {file_path}", 5000)
                self.setWindowTitle(f"Video Dubbing Studio v0.1 - {file_path}")
            else:
                self.statusBar().showMessage("Lỗi: Không thể đọc file project!", 5000)

    def generate_single_voice(self):
        row = self.properties_panel.current_index
        if row < 0: return

        if self.preview_player.playbackState() != QMediaPlayer.StoppedState:
            self.preview_player.stop()

        sub_item = self.subtitle_manager.get(row)
        if not sub_item: return

        # 1. Lấy cấu hình từ UI
        voice_id = self.properties_panel.cbo_voice.currentText()
        speed = self.properties_panel.sld_speed.value() / 100.0
        emotion = self.properties_panel.cbo_emotion.currentText()

        # Cập nhật Manager
        self.subtitle_manager.update_voice_settings(row, voice_id, speed, 0.0, 1.0, emotion)

        # 2. Chuẩn bị đường dẫn xuất file tạm (sẽ hoàn thiện thư mục cache ở task S2.7)
        os.makedirs("cache/audio", exist_ok=True)
        output_path = f"cache/audio/sub_{sub_item.id:04d}_{sub_item.get_hash()}.wav"

        # 3. Tạo Task và Disable nút UI để tránh spam click
        task = TTSTask(
            subtitle_id=sub_item.id,
            text=self.properties_panel.txt_text.toPlainText(),
            voice_id=voice_id,
            speed=speed,
            pitch=0.0,
            emotion=emotion,
            output_path=output_path
        )

        self.subtitle_manager.set_audio_status(row, "generating")
        self.properties_panel.btn_generate.setEnabled(False)
        self.properties_panel.lbl_audio_status.setText("Status: ◷ Generating...")

        # 4. Khởi chạy luồng nền
        self.tts_worker = TTSWorker(self.tts_engine, [task])
        self.tts_worker.task_finished.connect(self.on_tts_finished)
        self.tts_worker.task_error.connect(self.on_tts_error)
        self.tts_worker.start()

    def on_tts_finished(self, sub_id, output_path, duration):
        row = self.properties_panel.current_index
        sub_item = self.subtitle_manager.get(row)

        if sub_item and sub_item.id == sub_id:
            self.subtitle_manager.set_audio_status(row, "generated", output_path, duration)
            self.properties_panel.btn_generate.setEnabled(True)
            self.properties_panel.btn_preview.setEnabled(True)
            self.properties_panel.lbl_audio_status.setText("Status: ✓ Generated")
            self.properties_panel.lbl_audio_duration.setText(f"Duration: {duration:.2f} s")
            self.statusBar().showMessage(f"Tạo Voice thành công cho ID: {sub_id}", 5000)

    def on_tts_error(self, sub_id, error_msg):
        row = self.properties_panel.current_index
        sub_item = self.subtitle_manager.get(row)

        if sub_item and sub_item.id == sub_id:
            self.subtitle_manager.set_audio_status(row, "error", error=error_msg)
            self.properties_panel.btn_generate.setEnabled(True)
            self.properties_panel.lbl_audio_status.setText("Status: ⚠ Error")
            self.statusBar().showMessage(f"Lỗi tạo Voice (ID: {sub_id}): {error_msg}", 5000)

    def toggle_preview_voice(self):
        """Xử lý bật/tắt khi nhấn nút Preview"""
        # Nếu đang phát thì dừng lại
        if self.preview_player.playbackState() == QMediaPlayer.PlayingState:
            self.preview_player.stop()
            return

        row = self.properties_panel.current_index
        if row < 0: return

        sub_item = self.subtitle_manager.get(row)
        if not sub_item or not sub_item.audio_path: return

        # Kiểm tra file có tồn tại thật trong ổ cứng không
        if os.path.exists(sub_item.audio_path):
            self.preview_player.setSource(QUrl.fromLocalFile(sub_item.audio_path))
            self.preview_player.play()
        else:
            self.statusBar().showMessage("Lỗi: Không tìm thấy file Audio trong thư mục cache!", 5000)
            self.subtitle_manager.set_audio_status(row, "error", error="File not found")
            self.properties_panel.lbl_audio_status.setText("Status: ⚠ Error")

    def on_preview_state_changed(self, state):
        """Tự động đổi Text của nút dựa vào trạng thái phát"""
        if state == QMediaPlayer.PlayingState:
            self.properties_panel.btn_preview.setText("■ Stop")
        else:
            self.properties_panel.btn_preview.setText("▶ Preview")

            # THÊM LOGIC NÀY: Giải phóng file lock trên Windows khi âm thanh dừng
            if state == QMediaPlayer.StoppedState:
                self.preview_player.setSource(QUrl())

    def action_generate_all_pending(self):
        """Kích hoạt tạo âm thanh hàng loạt cho các dòng chưa có audio."""
        pending_items = self.subtitle_manager.get_pending_items()
        if not pending_items:
            self.statusBar().showMessage("Không có phụ đề nào cần tạo Audio.", 5000)
            return

        # Dừng preview để nhả file (tránh xung đột nếu đang ghi đè)
        if self.preview_player.playbackState() != QMediaPlayer.StoppedState:
            self.preview_player.stop()

        # Chuẩn bị thư mục và danh sách Task
        os.makedirs("cache/audio", exist_ok=True)
        tasks = []
        for sub in pending_items:
            # Lấy cấu hình voice hiện tại của từng dòng
            output_path = f"cache/audio/sub_{sub.id:04d}_{sub.get_hash()}.wav"
            tasks.append(TTSTask(
                subtitle_id=sub.id,
                text=sub.text,
                voice_id=sub.voice_id,
                speed=sub.speed,
                pitch=sub.pitch,
                emotion=sub.emotion,
                output_path=output_path
            ))

        # Khởi tạo Progress Dialog không chặn Main Thread
        self.progress_dialog = QProgressDialog("Đang nạp mô hình TTS...", "Cancel", 0, len(tasks), self)
        self.progress_dialog.setWindowTitle("Batch Generate")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        # Khởi chạy Worker
        self.tts_worker = TTSWorker(self.tts_engine, tasks)
        self.tts_worker.task_started.connect(self.on_batch_task_started)
        self.tts_worker.task_finished.connect(self.on_batch_task_finished)
        self.tts_worker.task_error.connect(self.on_batch_task_error)
        self.tts_worker.all_completed.connect(self.on_batch_completed)

        # Cho phép người dùng bấm Cancel để dừng giữa chừng
        self.progress_dialog.canceled.connect(self.tts_worker.cancel)

        self.tts_worker.start()

    def on_batch_task_started(self, sub_id):
        if hasattr(self, 'progress_dialog') and not self.progress_dialog.wasCanceled():
            self.progress_dialog.setLabelText(f"Đang xử lý phụ đề ID: {sub_id}...")

    def on_batch_task_finished(self, sub_id, output_path, duration):
        # 1. Cập nhật Data Model
        sub_item = self.subtitle_manager.get_by_id(sub_id)
        if sub_item:
            sub_item.audio_status = "generated"
            sub_item.audio_path = output_path
            sub_item.audio_duration = duration

        # 2. Cập nhật UI Progress
        if hasattr(self, 'progress_dialog') and not self.progress_dialog.wasCanceled():
            self.progress_dialog.setValue(self.progress_dialog.value() + 1)

        # 3. Đồng bộ giao diện Properties nếu đang chọn trúng dòng vừa tạo xong
        current_row = self.properties_panel.current_index
        if current_row >= 0:
            current_sub = self.subtitle_manager.get(current_row)
            if current_sub and current_sub.id == sub_id:
                self.properties_panel.lbl_audio_status.setText("Status: ✓ Generated")
                self.properties_panel.lbl_audio_duration.setText(f"Duration: {duration:.2f} s")
                self.properties_panel.btn_preview.setEnabled(True)

    def on_batch_task_error(self, sub_id, error_msg):
        sub_item = self.subtitle_manager.get_by_id(sub_id)
        if sub_item:
            sub_item.audio_status = "error"
            sub_item.audio_error = error_msg

    def on_batch_completed(self):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(self.progress_dialog.maximum())

        # Báo cho bảng TableView vẽ lại để hiển thị cập nhật mới nhất
        self.subtitle_table.model.update_data(self.subtitle_manager.get_all())
        self.statusBar().showMessage("Tiến trình tạo Audio hàng loạt hoàn tất.", 5000)

    def auto_save_settings(self):
        """Tự động lưu khi người dùng thay đổi cấu hình qua giao diện mà không cần bấm nút Save"""
        # Nếu đang không chọn dòng nào thì bỏ qua
        if self.properties_panel.current_index < 0:
            return
            
        # Gọi lại hàm save đã viết sẵn ở S2.7
        self.save_subtitle_changes()

    def eventFilter(self, source, event):
        """Bắt sự kiện FocusOut của ô TextEdit để auto-save chữ"""
        from PySide6.QtCore import QEvent
        if source is self.properties_panel.txt_text and event.type() == QEvent.FocusOut:
            self.auto_save_settings()
        return super().eventFilter(source, event)