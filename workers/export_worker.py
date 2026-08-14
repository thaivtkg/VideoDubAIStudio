import os
import subprocess

from pydub import AudioSegment
from PySide6.QtCore import QThread, Signal


class ExportWorker(QThread):
    progress = Signal(int, str)       # % hoàn thành, câu thông báo
    finished = Signal(str)            # Đường dẫn file output
    error = Signal(str)               # Lỗi nếu có

    def __init__(self, video_path, clips, output_path, video_duration_ms, export_format="mp4"):
        super().__init__()
        self.video_path = video_path
        self.clips = clips            # Danh sách AudioClip từ TimelineManager
        self.output_path = output_path
        self.video_duration_ms = video_duration_ms
        self.export_format = export_format

        self.process = None       # Giữ reference của FFmpeg process
        self._is_cancelled = False

    def cancel(self):
        """Được gọi từ UI khi user bấm nút Cancel trên Dialog"""
        self._is_cancelled = True
        if self.process:
            self.process.terminate() # Bắn tín hiệu dừng an toàn cho FFmpeg
            self.process.wait()

    def run(self):
        temp_audio_path = "cache/temp_master_audio.wav"
        try:
            self.progress.emit(10, "Đang khởi tạo trục âm thanh...")

            # 1. Tính toán thời lượng tối thiểu cần thiết cho Master Track
            # (Phòng trường hợp câu thoại cuối cùng dài hơn thời lượng video gốc)
            max_clip_end_ms = self.video_duration_ms
            for clip in self.clips:
                clip_end_ms = int((clip.start_time + clip.duration) * 1000)
                if clip_end_ms > max_clip_end_ms:
                    max_clip_end_ms = clip_end_ms

            # Tạo Master Silent với chiều dài an toàn nhất
            master_audio = AudioSegment.silent(duration=max_clip_end_ms, frame_rate=44100)

            # 2. Overlay các audio vào Master Track
            total_clips = len(self.clips)
            for i, clip in enumerate(self.clips):
                if self._is_cancelled:
                    return
                
                if os.path.exists(clip.audio_path):
                    self.progress.emit(
                        10 + int(40 * (i / total_clips)), 
                        f"Đang hòa trộn Audio ID: {clip.subtitle_id}..."
                    )
                    clip_audio = AudioSegment.from_wav(clip.audio_path)
                    position_ms = int(clip.start_time * 1000)
                    master_audio = master_audio.overlay(clip_audio, position=position_ms)

            self.progress.emit(60, "Đang xuất file âm thanh tổng (WAV)...")
            
            if self._is_cancelled:
                return
            
            # 3. Kịch bản Xuất WAV trực tiếp
            if self.export_format == "wav":
                master_audio.export(self.output_path, format="wav")
                self.progress.emit(100, "Hoàn tất xuất file Audio (WAV)!")
                self.finished.emit(self.output_path)
                return

            # 4. Kịch bản Xuất MP4 (Cần xuất file Temp trước rồi dùng FFmpeg ghép vào)
            master_audio.export(temp_audio_path, format="wav")
            self.progress.emit(80, "Đang ghép Âm thanh vào Video (Muxing)...")
            
            command = [
                "ffmpeg", "-y",
                "-i", self.video_path,
                "-i", temp_audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                self.output_path
            ]
            
            self.process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            stdout, stderr = self.process.communicate()
            
            if self._is_cancelled:
                return
            
            if self.process.returncode != 0:
                raise Exception(f"Lỗi FFmpeg: {stderr.decode('utf-8', errors='ignore')}")

            self.progress.emit(100, "Hoàn tất xuất Video!")
            self.finished.emit(self.output_path)

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
        finally:
            # 5. Luôn dọn dẹp file rác dù thành công, lỗi hay bị huỷ ngang
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)