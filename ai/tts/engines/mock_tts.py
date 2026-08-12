import math
import os
import struct
import time
import wave

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

    def generate(self, text, voice_id, speed, pitch, emotion, output_path, subtitle_id=1):
        """Sinh ra file âm thanh Synthetic (sóng Sine Beep) có tần số riêng biệt cho từng ID"""
        # 1. Tính toán thời lượng dựa trên độ dài chữ và speed
        base_duration = len(text) * 0.08
        if base_duration < 0.5:
            base_duration = 0.5
        actual_duration = base_duration / speed

        sample_rate = 44100
        num_samples = int(actual_duration * sample_rate)

        # 2. Tạo tần số âm thanh riêng cho từng Subtitle ID để dễ nhận biết khi Overlap
        # ID 1 -> 440Hz (Nốt La), ID 2 -> 490Hz, ID 3 -> 540Hz...
        frequency = 440 + ((subtitle_id % 10) * 50)
        amplitude = 16000  # Biên độ sóng âm vừa đủ nghe (Âm lượng ~ 50%)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with wave.open(output_path, 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            audio_data = bytearray()
            fade_samples = int(sample_rate * 0.05)  # Fade in/out 50ms chống giật loa

            for i in range(num_samples):
                # Công thức toán học tạo sóng Sine
                sample_val = math.sin(2 * math.pi * frequency * i / sample_rate)

                # Áp dụng Fade-in và Fade-out ở đầu/cuối clip
                if i < fade_samples:
                    sample_val *= i / fade_samples
                elif i > num_samples - fade_samples:
                    sample_val *= (num_samples - i) / fade_samples

                packed_value = struct.pack('<h', int(sample_val * amplitude))
                audio_data.extend(packed_value)

            wav_file.writeframes(audio_data)

        return actual_duration