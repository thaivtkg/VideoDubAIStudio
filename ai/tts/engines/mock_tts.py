import wave
import time
from ai.tts.base_tts import BaseTTSEngine

class MockTTSEngine(BaseTTSEngine):
    def get_engine_name(self) -> str:
        return "Mock TTS (Offline Test)"

    def get_supported_languages(self) -> list[str]:
        return ["vi", "en"]

    def get_voices(self, language: str) -> list[dict]:
        return [
            {"id": "female_01", "name": "Nữ 01", "emotions": ["Natural", "Happy"]},
            {"id": "male_01", "name": "Nam 01", "emotions": ["Natural", "Serious"]}
        ]

    def load_model(self) -> bool:
        # Giả lập độ trễ khi load model vào VRAM
        time.sleep(0.5)
        return True

    def unload_model(self):
        pass

    def generate(self, text: str, voice_id: str, speed: float, pitch: float, emotion: str, output_path: str) -> bool:
        try:
            # Giả lập thời gian AI xử lý (phụ thuộc độ dài text)
            time.sleep(min(len(text) * 0.05, 2.0))

            # Sinh file WAV tĩnh dài 2 giây
            sample_rate = 44100
            duration = 2.0
            n_frames = int(sample_rate * duration)

            with wave.open(output_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2) # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b'\x00\x00' * n_frames)

            return True
        except Exception as e:
            # Lỗi ở tầng Infra phải được ném lên để Worker bắt và truyền về UI
            raise e