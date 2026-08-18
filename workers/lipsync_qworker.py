from PySide6.QtCore import QThread, Signal, QObject

class LipSyncSignals(QObject):
    started = Signal()
    stage_changed = Signal(str)           # Báo cáo giai đoạn (VD: "Đang render AI...")
    progress = Signal(int, int)           # current_frame, total_frames (dùng cho thanh Loading)
    finished = Signal(dict)               # Trả về kết quả JSON khi hoàn thành
    error = Signal(str)                   # Báo lỗi để hiển thị Popup
    cancelled = Signal()

class LipSyncQWorker(QThread):
    def __init__(self, manager, engine_name, video_path, audio_path, output_path, config):
        super().__init__()
        self.manager = manager
        self.engine_name = engine_name
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self.config = config
        
        self.signals = LipSyncSignals()
        self._is_cancelled = False

    def run(self):
        """Khối lệnh này chạy trên một luồng hoàn toàn độc lập, không làm treo UI"""
        self.signals.started.emit()
        self.signals.stage_changed.emit("Khởi tạo tiến trình Lip Sync (Isolated Process)...")
        
        try:
            # Nếu người dùng bấm Hủy trước khi chạy
            if self._is_cancelled:
                self.signals.cancelled.emit()
                return

            self.signals.stage_changed.emit(f"Đang render bằng {self.engine_name.upper()}...")
            
            # Gọi Manager để kích hoạt subprocess. 
            # Vì đang ở QThread, subprocess.run() sẽ block luồng ngầm này, GUI vẫn mượt mà!
            result = self.manager.process_lipsync(
                self.engine_name,
                self.video_path,
                self.audio_path,
                self.output_path,
                self.config
            )
            
            if self._is_cancelled:
                self.signals.cancelled.emit()
            else:
                self.signals.finished.emit(result)
                
        except Exception as e:
            self.signals.error.emit(f"Lỗi hệ thống: {str(e)}")
            
    def cancel(self):
        """Hàm kích hoạt cờ hủy (Dành cho nút Cancel trên giao diện)"""
        self._is_cancelled = True
        # Tương lai sẽ thêm logic kill PID của subprocess tại đây   