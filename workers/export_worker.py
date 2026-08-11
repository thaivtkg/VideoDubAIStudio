import os
import subprocess
from PySide6.QtCore import QThread, Signal
from pydub import AudioSegment

class ExportWorker(QThread):
    progress = Signal(int, str)       # % hoàn thành, câu thông báo
    finished = Signal(str)            # Đường dẫn file output
    error = Signal(str)               # Lỗi nếu có

    def __init__(self, video_path, clips, output_path, video_duration_ms):
        super().__init__()
        self.video_path = video_path
        self.clips = clips            # Danh sách AudioClip từ TimelineManager
        self.output_path = output_path
        self.video_duration_ms = video_duration_ms

    def run(self):
        try:
            self.progress.emit(10, "Đang khởi tạo trục âm thanh...")
            
            # 1. Tạo một track âm thanh trống có độ dài bằng với Video
            # (Đảm bảo file âm thanh đầu ra có cùng chiều dài với video gốc)
            master_audio = AudioSegment.silent(duration=self.video_duration_ms)

            # 2. Trộn (Overlay) từng file âm thanh nhỏ vào track chính
            total_clips = len(self.clips)
            for i, clip in enumerate(self.clips):
                if os.path.exists(clip.audio_path):
                    self.progress.emit(10 + int(40 * (i / total_clips)), f"Đang hòa trộn Audio ID: {clip.subtitle_id}...")
                    
                    # Đọc file audio của từng câu phụ đề
                    clip_audio = AudioSegment.from_wav(clip.audio_path)
                    
                    # Chèn vào đúng vị trí start_time (tính bằng mili-giây)
                    position_ms = int(clip.start_time * 1000)
                    master_audio = master_audio.overlay(clip_audio, position=position_ms)

            # 3. Xuất track âm thanh tổng ra file tạm
            self.progress.emit(60, "Đang xuất file âm thanh tổng (WAV)...")
            temp_audio_path = "cache/temp_master_audio.wav"
            master_audio.export(temp_audio_path, format="wav")

            # 4. Dùng FFmpeg để ghép Audio tổng vào Video gốc (Tạm thời thay thế hoàn toàn tiếng gốc)
            self.progress.emit(80, "Đang ghép Âm thanh vào Video (Muxing)...")
            
            command = [
                "ffmpeg",
                "-y",                           # Ghi đè file nếu đã tồn tại
                "-i", self.video_path,          # Input Video
                "-i", temp_audio_path,          # Input Audio lồng tiếng
                "-c:v", "copy",                 # Copy y nguyên hình ảnh (render siêu tốc)
                "-c:a", "aac",                  # Encode audio sang chuẩn MP4
                "-map", "0:v:0",                # Lấy hình từ Input 0 (Video)
                "-map", "1:a:0",                # Lấy tiếng từ Input 1 (Audio dubbing)
                self.output_path
            ]
            
            # Khởi chạy FFmpeg ngầm, ẩn cửa sổ cmd
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Lỗi FFmpeg: {stderr.decode('utf-8', errors='ignore')}")

            # Dọn dẹp file tạm
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

            self.progress.emit(100, "Hoàn tất!")
            self.finished.emit(self.output_path)

        except Exception as e:
            self.error.emit(str(e))