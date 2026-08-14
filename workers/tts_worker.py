from dataclasses import dataclass
from PySide6.QtCore import QThread, Signal


@dataclass
class TTSTask:
    subtitle_id: int
    text: str
    voice_id: str
    speed: float
    pitch: float
    emotion: str
    output_path: str


class TTSWorker(QThread):
    # Signals giao tiếp một chiều: Worker -> UI
    task_started = Signal(int)  # (subtitle_id)
    task_finished = Signal(int, str, float)  # (subtitle_id, output_path, duration)
    task_error = Signal(int, str)  # (subtitle_id, error_message)
    all_completed = Signal()  # Báo hiệu hoàn tất Batch

    def __init__(self, engine, tasks: list[TTSTask]):
        super().__init__()
        self.engine = engine
        self.tasks = tasks
        self._is_cancelled = False

    def run(self):
        # 1. Nạp model một lần duy nhất trước khi chạy Batch
        try:
           if not self.engine.load_model():
              # [SỬA] Đảm bảo luôn thông báo và đóng Progress Dialog ở Main Thread
              self.task_error.emit(-1, "Không thể load mô hình TTS. Tiến trình bị hủy.")
              self.all_completed.emit() # Ép Progress Dialog đóng lại an toàn
              return
        except Exception as e:
             self.task_error.emit(-1, f"Lỗi khởi tạo TTS: {str(e)}")
             self.all_completed.emit()
             return

        # 2. Xử lý tuần tự các task
        for task in self.tasks:
            if self._is_cancelled:
                break

            self.task_started.emit(task.subtitle_id)
            try:
                duration = self.engine.generate(
                    text=task.text,
                    voice_id=task.voice_id,
                    speed=task.speed,
                    pitch=task.pitch,
                    emotion=task.emotion,
                    output_path=task.output_path,
                    subtitle_id=task.subtitle_id
                )

                if duration and duration > 0:
                    # TRUYỀN DURATION THỰC TẾ XUỐNG UI
                    self.task_finished.emit(task.subtitle_id, task.output_path, duration)
                else:
                    self.task_error.emit(task.subtitle_id, "TTS Engine trả về lỗi không xác định.")

            except Exception as e:
                self.task_error.emit(task.subtitle_id, str(e))

        # 3. Giải phóng model khi xong việc hoặc bị Cancel
        self.engine.unload_model()
        self.all_completed.emit()

    def cancel(self):
        self._is_cancelled = True