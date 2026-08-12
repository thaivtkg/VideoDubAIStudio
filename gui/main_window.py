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
from core.audio_manager import AudioManager
from core.project_manager import ProjectManager
from core.srt_parser import parse_srt
from core.subtitle_manager import SubtitleManager
from core.timeline_manager import TimelineManager
from gui.widgets.audio_timeline import AudioTimelineWidget
from gui.widgets.project_panel import ProjectPanelWidget
from gui.widgets.properties_panel import PropertiesPanelWidget
from gui.widgets.subtitle_table import SubtitleTableWidget
from gui.widgets.video_player import VideoPlayerWidget
from workers.export_worker import ExportWorker
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
        self.timeline_manager = TimelineManager()    # MỚI
        self.audio_manager = AudioManager()
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
        file_menu.addAction("Export Video (MP4)...", self.action_export_video)
        file_menu.addAction("Export Audio (WAV)...", self.action_export_audio)
        file_menu.addAction("Exit", self.close)

        voice_menu = menubar.addMenu("Voice")
        voice_menu.addAction("Generate All Pending", self.action_generate_all_pending)
        voice_menu.addAction("Auto-Fit Overlapping Audio", self.action_auto_fit)

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
        
        # [MỚI] Bọc Properties Panel vào thanh cuộn (ScrollArea) để không bị che khuất
        from PySide6.QtWidgets import QFrame, QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(self.properties_panel)
        
        dock_properties.setWidget(scroll_area)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_properties)



        # 4. Bottom Dock: Subtitle Table
        self.dock_table = QDockWidget("Subtitle Timeline", self)
        self.subtitle_table = SubtitleTableWidget()
        self.dock_table.setWidget(self.subtitle_table)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_table)

        # 5. Timeline Panel (MỚI)
        self.timeline_widget = AudioTimelineWidget()
        self.dock_timeline = QDockWidget("Audio Timeline", self)
        self.dock_timeline.setWidget(self.timeline_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)
        
        # [QUAN TRỌNG]: Tách Dock theo chiều dọc để Timeline chiếm toàn bộ chiều ngang bên dưới Table
        self.splitDockWidget(self.dock_table, self.dock_timeline, Qt.Vertical)

        # 6. Kết nối sự kiện (Signals / Slots)
        self.subtitle_table.selectionModel().selectionChanged.connect(self.on_subtitle_selected)
        self.properties_panel.btn_save.clicked.connect(self.save_subtitle_changes)
        self.properties_panel.btn_generate.clicked.connect(self.generate_single_voice)
        self.properties_panel.btn_preview.clicked.connect(self.toggle_preview_voice)
        self.preview_player.playbackStateChanged.connect(self.on_preview_state_changed)
        
        self.video_player.player.positionChanged.connect(self.sync_audio_with_video)
        self.video_player.player.playbackStateChanged.connect(self.handle_video_state_change)
        self.video_player.player.durationChanged.connect(self.timeline_widget.set_duration)
        self.video_player.player.positionChanged.connect(self.timeline_widget.set_position)

        # THÊM LOGIC AUTO-SAVE TẠI ĐÂY
        # Bắt sự kiện khi người dùng thay đổi Voice, Speed hoặc Emotion
        self.properties_panel.cbo_voice.currentIndexChanged.connect(self.auto_save_settings)
        self.properties_panel.cbo_emotion.currentIndexChanged.connect(self.auto_save_settings)
        # Sử dụng sliderReleased thay vì valueChanged để tránh việc save liên tục hàng chục lần khi người dùng đang kéo chuột
        self.properties_panel.sld_speed.sliderReleased.connect(self.auto_save_settings)
        
        # Kết nối sự kiện mất focus (người dùng gõ xong chữ rồi click ra ngoài) cho trường Text
        self.properties_panel.txt_text.installEventFilter(self)
        self.video_player.seek_requested.connect(self.on_user_seek)

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
                # Nạp dữ liệu vào SubtitleManager (Hàm này đã tự clear danh sách cũ)
                self.subtitle_manager.load_subtitles(subtitles_data)

                # Cập nhật Table và Panel
                self.subtitle_table.model.update_data(self.subtitle_manager.get_all())
                self.project_panel.update_srt(file_path)

                # [SỬA TẠI ĐÂY] Đồng bộ Timeline ngay lập tức để xóa Audio Clips của SRT cũ
                self.update_timeline_data()

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
                self.properties_panel.btn_generate.setEnabled(True) # LUÔN BẬT
                
            elif sub_item.audio_status == "generating":
                self.properties_panel.lbl_audio_status.setText("Status: ◷ Generating...")
                self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                self.properties_panel.btn_preview.setEnabled(False)
                self.properties_panel.btn_generate.setEnabled(False) # KHOÁ LẠI VÌ ĐANG CHẠY
                
            elif sub_item.audio_status == "error":
                self.properties_panel.lbl_audio_status.setText("Status: ⚠ Error")
                self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                self.properties_panel.btn_preview.setEnabled(False)
                self.properties_panel.btn_generate.setEnabled(True) # LUÔN BẬT
                
            else:
                self.properties_panel.lbl_audio_status.setText("Status: ○ Not Generated")
                self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                self.properties_panel.btn_preview.setEnabled(False)
                self.properties_panel.btn_generate.setEnabled(True) # LUÔN BẬT


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
                    was_generated = (sub_item.audio_status == "generated")
                    
                    sub_item.audio_status = "not_generated"
                    sub_item.audio_path = ""
                    sub_item.audio_duration = 0.0

                    # Reset UI Properties
                    self.properties_panel.lbl_audio_status.setText("Status: ○ Not Generated")
                    self.properties_panel.lbl_audio_duration.setText("Duration: 0.00 s")
                    self.properties_panel.btn_preview.setEnabled(False)
                    
                    if was_generated:
                        self.statusBar().showMessage("Cấu hình thay đổi, yêu cầu Generate lại Audio.", 5000)
                    else:
                        self.statusBar().showMessage(f"Đã cập nhật cấu hình cho ID: {sub_item.id}", 5000)
                else:
                    self.statusBar().showMessage(f"Đã cập nhật thông số thời gian cho ID: {sub_item.id}", 5000)

                # Cập nhật TableView
                top_left = self.subtitle_table.model.index(row, 1)
                bottom_right = self.subtitle_table.model.index(row, 3)
                self.subtitle_table.model.dataChanged.emit(top_left, bottom_right)
                self.update_timeline_data()

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
                    self.update_timeline_data()

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
        # 1. Lấy dữ liệu item chính xác dựa vào ID của luồng nền trả về
        sub_item = self.subtitle_manager.get_by_id(sub_id)
        if not sub_item: return

        # Tìm row index thực tế trên TableView
        all_subs = self.subtitle_manager.get_all()
        actual_row = -1
        for i, sub in enumerate(all_subs):
            if sub.id == sub_id:
                actual_row = i
                break

        if actual_row != -1:
            # 2. Cập nhật Model và ép TableView vẽ lại ô trạng thái (cột 5)
            self.subtitle_manager.set_audio_status(actual_row, "generated", output_path, duration)
            index = self.subtitle_table.model.index(actual_row, 5)
            self.subtitle_table.model.dataChanged.emit(index, index)
            self.update_timeline_data() # Đồng bộ xuống Audio Timeline

        # 3. Mở khóa lại nút Generate (Luồng nền đã rảnh)
        self.properties_panel.btn_generate.setEnabled(True)
        self.statusBar().showMessage(f"Tạo Voice thành công cho ID: {sub_id}", 5000)

        # 4. Chỉ cập nhật giao diện PropertiesPanel nếu người dùng đang ĐỨNG TRÊN đúng dòng vừa chạy xong
        current_row = self.properties_panel.current_index
        if current_row == actual_row:
            self.properties_panel.lbl_audio_status.setText("Status: ✓ Generated")
            self.properties_panel.lbl_audio_duration.setText(f"Duration: {duration:.2f} s")
            self.properties_panel.btn_preview.setEnabled(True)

    def on_tts_error(self, sub_id, error_msg):
        sub_item = self.subtitle_manager.get_by_id(sub_id)
        if not sub_item: return

        all_subs = self.subtitle_manager.get_all()
        actual_row = -1
        for i, sub in enumerate(all_subs):
            if sub.id == sub_id:
                actual_row = i
                break

        if actual_row != -1:
            self.subtitle_manager.set_audio_status(actual_row, "error", error=error_msg)
            index = self.subtitle_table.model.index(actual_row, 5)
            self.subtitle_table.model.dataChanged.emit(index, index)

        self.properties_panel.btn_generate.setEnabled(True)
        self.statusBar().showMessage(f"Lỗi tạo Voice (ID: {sub_id}): {error_msg}", 5000)

        current_row = self.properties_panel.current_index
        if current_row == actual_row:
            self.properties_panel.lbl_audio_status.setText("Status: ⚠ Error")
            self.properties_panel.btn_preview.setEnabled(False)

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
            # sub_item.audio_error = error_msg

        # [QUAN TRỌNG] Phải tăng thanh tiến trình kể cả khi task đó bị lỗi, nếu không UI sẽ treo ở 0% mãi mãi
        if hasattr(self, 'progress_dialog') and not self.progress_dialog.wasCanceled():
            self.progress_dialog.setValue(self.progress_dialog.value() + 1)
            
        # Cập nhật giao diện Properties nếu người dùng đang click trúng dòng bị lỗi
        current_row = self.properties_panel.current_index
        if current_row >= 0:
            current_sub = self.subtitle_manager.get(current_row)
            if current_sub and current_sub.id == sub_id:
                self.properties_panel.lbl_audio_status.setText("Status: ⚠ Error")
                self.properties_panel.btn_preview.setEnabled(False)

    def on_batch_completed(self):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(self.progress_dialog.maximum())

        # Báo cho bảng TableView vẽ lại để hiển thị cập nhật mới nhất
        self.subtitle_table.model.update_data(self.subtitle_manager.get_all())
        self.update_timeline_data()
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

    def update_timeline_data(self):
        """Cập nhật dữ liệu cho TimelineManager mỗi khi có thay đổi về Audio"""
        subtitles = self.subtitle_manager.get_all()
        self.timeline_manager.sync_from_subtitles(subtitles)
        # THÊM ĐOẠN NÀY: Ép đồng bộ chiều dài video (đề phòng tín hiệu bị lỡ khi load)
        if hasattr(self, 'video_player') and self.video_player.player.duration() > 0:
            self.timeline_widget.set_duration(self.video_player.player.duration())

        self.timeline_widget.update_data(subtitles)

    def sync_audio_with_video(self, position_ms):
        """Kích hoạt bởi VideoPlayer mỗi khi video tiến lên, truyền mốc thời gian cho AudioManager"""
        if self.video_player.player.playbackState() == QMediaPlayer.PlayingState:
            current_time_sec = position_ms / 1000.0
            active_clips = self.timeline_manager.get_clips_in_range(current_time_sec)
            self.audio_manager.tick(position_ms, active_clips)

    def handle_video_state_change(self, state):
        """Ngắt toàn bộ âm thanh lồng tiếng nếu video bị Tạm dừng (Pause) hoặc Dừng (Stop)"""
        if state in (QMediaPlayer.PausedState, QMediaPlayer.StoppedState):
            self.audio_manager.stop_all()

    def action_auto_fit(self):
        """S3.4: Tự động điều chỉnh Speed cho các câu bị Overlap (Audio dài hơn Subtitle)"""
        pending_tasks = False
        overflow_warning = False
        
        for sub in self.subtitle_manager.get_all():
            if sub.audio_status == "generated" and sub.audio_duration > 0:
                target_duration = sub.end_time - sub.start_time
                
                # Nếu Audio thực tế dài hơn thời gian cho phép của Subtitle
                # [SỬA TẠI ĐÂY] Đưa toàn bộ logic clamp và cập nhật vào trong IF
                if sub.audio_duration > target_duration:
                    ratio = sub.audio_duration / target_duration
                    new_speed = sub.speed * ratio
                    
                    # Kiểm tra trần giới hạn
                    if new_speed > 2.0:
                        new_speed = 2.0
                        overflow_warning = True 
                        
                    # Gán thông số mới
                    sub.speed = new_speed
                    
                    # Reset trạng thái
                    sub.audio_status = "not_generated"
                    sub.audio_path = ""
                    sub.audio_duration = 0.0
                    pending_tasks = True
                    
        if pending_tasks:
            # Vẽ lại Table và Timeline
            self.subtitle_table.model.update_data(self.subtitle_manager.get_all())
            self.update_timeline_data()
            
            # Cập nhật Properties Panel nếu đang trúng dòng vừa bị reset
            current_row = self.properties_panel.current_index
            if current_row >= 0:
                current_sub = self.subtitle_manager.get(current_row)
                self.properties_panel.sld_speed.setValue(int(current_sub.speed * 100))
                self.properties_panel.lbl_audio_status.setText("Status: ○ Not Generated")
            
            self.statusBar().showMessage("Đã tính toán Auto-Fit. Đang tạo lại Audio...", 5000)
            
            # Tự động kích hoạt Batch Generate để sinh lại các file với Speed mới
            self.action_generate_all_pending()
            if overflow_warning:
                self.statusBar().showMessage("Cảnh báo: Một số câu quá dài đã bị giới hạn ở tốc độ tối đa (2.0x) và vẫn bị chèn lấn!", 8000)
            else:
                self.statusBar().showMessage("Đã tính toán Auto-Fit thành công trong giới hạn an toàn.", 5000)
        else:
            self.statusBar().showMessage("Không có câu thoại nào bị chèn lấn (Overlap).", 5000)

    def action_export_video(self):
        """Kích hoạt xuất file MP4"""
        self._start_export(format_type="mp4", file_filter="Video Files (*.mp4)")

    def action_export_audio(self):
        """Kích hoạt xuất file WAV (Master Audio)"""
        self._start_export(format_type="wav", file_filter="Audio Files (*.wav)")

    def _start_export(self, format_type, file_filter):
        """Hàm dùng chung để khởi chạy Export Worker"""
        if not hasattr(self.project_manager.current_project, 'video_path') or not self.project_manager.current_project.video_path:
            self.statusBar().showMessage("Lỗi: Vui lòng Import Video gốc trước khi Export!", 5000)
            return

        title = "Xuất Video thành phẩm" if format_type == "mp4" else "Xuất Âm thanh tổng"
        output_path, _ = QFileDialog.getSaveFileName(self, title, "", file_filter)
        if not output_path:
            return

        self.update_timeline_data()
        clips = list(self.timeline_manager.clips.values())
        
        if not clips:
            self.statusBar().showMessage("Không có âm thanh nào trên Timeline để xuất!", 5000)
            return
            
        video_duration_ms = self.video_player.player.duration()
        if video_duration_ms <= 0:
            self.statusBar().showMessage("Lỗi: Không xác định được thời lượng Video.", 5000)
            return

        # Hiển thị UI Progress
        self.export_progress = QProgressDialog(f"Đang chuẩn bị xuất {format_type.upper()}...", "Hủy (An toàn)", 0, 100, self)
        self.export_progress.setWindowTitle(f"Exporting {format_type.upper()}")
        self.export_progress.setWindowModality(Qt.WindowModal)
        self.export_progress.setMinimumDuration(0)
        self.export_progress.setValue(0)

        # Truyền format_type xuống Worker
        self.export_worker = ExportWorker(
            video_path=self.project_manager.current_project.video_path,
            clips=clips,
            output_path=output_path,
            video_duration_ms=video_duration_ms,
            export_format=format_type
        )
        
        self.export_worker.progress.connect(self.on_export_progress)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.error.connect(self.on_export_error)
        
        # [QUAN TRỌNG NHẤT] Gọi đúng hàm .cancel() đã viết thay vì .terminate() mặc định
        self.export_progress.canceled.connect(self.export_worker.cancel) 
        
        self.export_worker.start()
        
    def on_export_progress(self, value, text):
        if hasattr(self, 'export_progress') and not self.export_progress.wasCanceled():
            self.export_progress.setValue(value)
            self.export_progress.setLabelText(text)

    def on_export_finished(self, output_path):
        if hasattr(self, 'export_progress'):
            self.export_progress.setValue(100)
        self.statusBar().showMessage(f"Xuất video thành công: {output_path}", 10000)

    def on_export_error(self, error_msg):
        if hasattr(self, 'export_progress'):
            self.export_progress.cancel()
        self.statusBar().showMessage(f"Lỗi xuất video: {error_msg}", 10000)

    def on_user_seek(self, position_ms):
        """Khi người dùng Seek, ép AudioManager nhả toàn bộ Player và resync lại từ đầu"""
        self.audio_manager.stop_all()
        self.audio_manager.active_clips.clear()
        current_time_sec = position_ms / 1000.0
        active_clips = self.timeline_manager.get_clips_in_range(current_time_sec)
        self.audio_manager.tick(position_ms, active_clips, is_seeking=True)