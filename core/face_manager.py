import os
import json
import hashlib
import cv2
from ai.face.mediapipe_detector import MediaPipeFaceDetector

class FaceManager:
    def __init__(self, cache_dir="cache/lipsync"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.detector = MediaPipeFaceDetector()

    def _get_video_hash(self, video_path: str) -> str:
        """Tạo mã băm độc nhất dựa trên đường dẫn và dung lượng file video"""
        file_stat = os.stat(video_path)
        unique_string = f"{video_path}_{file_stat.st_size}_{file_stat.st_mtime}"
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def process_and_cache(self, video_path: str, force_recalc=False) -> dict:
        """
        Quét toàn bộ video và lưu Cache. Nếu đã có cache thì trả về ngay.
        Đảm bảo Pipeline Phase 1 (Detect) chạy độc lập để tiết kiệm VRAM.
        """
        video_hash = self._get_video_hash(video_path)
        cache_file = os.path.join(self.cache_dir, f"{video_hash}_faces.json")

        # 1. Đọc từ Cache nếu tồn tại
        if os.path.exists(cache_file) and not force_recalc:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 2. Xử lý quét khuôn mặt nếu chưa có cache
        print(f"[FaceManager] Đang khởi tạo quét khuôn mặt cho: {os.path.basename(video_path)}")
        self.detector.load(device="cpu")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        face_data = {
            "fps": fps,
            "total_frames": total_frames,
            "frames": {}
        }

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            boxes = self.detector.detect(frame)
            if boxes:
                # Chỉ lưu khuôn mặt có độ tự tin cao nhất (Primary Face)
                best_face = max(boxes, key=lambda b: b.confidence)
                face_data["frames"][str(frame_idx)] = [best_face.x, best_face.y, best_face.width, best_face.height]
            
            frame_idx += 1

        cap.release()
        self.detector.unload() # Bắt buộc giải phóng RAM ngay sau khi quét xong

        # 3. Ghi ra file Cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(face_data, f)
            
        print(f"[FaceManager] Đã lưu cache khuôn mặt tại: {cache_file}")
        return face_data