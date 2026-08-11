import os
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

    def generate(self, text, voice_id, speed, pitch, emotion, output_path):
        """Giả lập AI tạo Audio có thời lượng phụ thuộc vào độ dài chữ và tốc độ Speed"""
        time.sleep(0.1)  # Giả lập độ trễ mạng để thấy Progress bar chạy
        
        # 1. Giả lập: Người bình thường đọc 1 ký tự mất khoảng 0.08 giây
        base_duration = len(text) * 0.08
        if base_duration < 0.5: 
            base_duration = 0.5  # Tối thiểu nửa giây cho một âm thanh
            
        # 2. Áp dụng ép tốc độ (Speed) từ Auto-Fit
        actual_duration = base_duration / speed
        
        # 3. Tạo file WAV trống (im lặng) có độ dài đúng bằng actual_duration
        sample_rate = 44100
        num_samples = int(actual_duration * sample_rate)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with wave.open(output_path, 'w') as wav_file:
            wav_file.setnchannels(1)           # Mono
            wav_file.setsampwidth(2)           # 16-bit
            wav_file.setframerate(sample_rate) # 44.1 kHz
            wav_file.writeframes(b'\x00\x00' * num_samples) # Ghi data rỗng
            
        # TRẢ VỀ DURATION THỰC TẾ thay vì True/False
        return actual_duration