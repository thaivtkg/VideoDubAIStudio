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
        
        self.schema_version = 1 
        # [UPGRADE]: Giới hạn số frame tối đa được níu giữ tọa độ cũ (15 frame ~ 0.5 giây)
        self.max_hold_frames = 15 

    def _get_video_hash(self, video_path: str) -> str:
        file_stat = os.stat(video_path)
        unique_string = f"{video_path}_{file_stat.st_size}_{file_stat.st_mtime}"
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def _clamp_box(self, box, frame_width, frame_height):
        """[FIX REVIEW 1]: Đảm bảo Box không bị âm hoặc tràn ra ngoài viền video"""
        x, y, w, h = box
        # Ép x, y >= 0 và không vượt quá chiều rộng/cao
        x = max(0, min(x, frame_width - 1))
        y = max(0, min(y, frame_height - 1))
        # Ép w, h tối thiểu là 1 và không tràn qua diện tích còn lại của khung hình
        w = max(1, min(w, frame_width - x))
        h = max(1, min(h, frame_height - y))
        return [int(x), int(y), int(w), int(h)]

    def process_and_cache(self, video_path: str, force_recalc=False) -> dict:
        video_hash = self._get_video_hash(video_path)
        cache_file = os.path.join(self.cache_dir, f"{video_hash}_faces.json")

        if os.path.exists(cache_file) and not force_recalc:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if cached_data.get("schema_version") == self.schema_version:
                        return cached_data
                    else:
                        print("[FaceManager] Phát hiện Cache cũ không tương thích. Khởi tạo quét lại...")
            except Exception:
                pass

        print(f"[FaceManager] Đang khởi tạo quét khuôn mặt cho: {os.path.basename(video_path)}")
        self.detector.load(device="cpu")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        face_data = {
            "schema_version": self.schema_version,
            "detector": "mediapipe",
            "video_hash": video_hash,
            "video_fps": fps,
            "width": width,
            "height": height,
            "total_frames": total_frames,
            "frames": {}
        }

        frame_idx = 0
        last_valid_box = None
        missing_frames_count = 0  # Bộ đếm số frame liên tiếp bị mất mặt
        default_box = [width // 4, height // 4, width // 2, height // 2] # Box an toàn giữa màn hình

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            boxes = self.detector.detect(frame)
            
            if boxes:
                best_face = max(boxes, key=lambda b: b.confidence)
                raw_box = [best_face.x, best_face.y, best_face.width, best_face.height]
                
                # Gọi hàm kẹp tọa độ trước khi lưu
                last_valid_box = self._clamp_box(raw_box, width, height)
                face_data["frames"][str(frame_idx)] = last_valid_box
                
                # Reset bộ đếm khi tìm thấy khuôn mặt
                missing_frames_count = 0 
            else:
                missing_frames_count += 1
                
                if last_valid_box is not None and missing_frames_count <= self.max_hold_frames:
                    # Níu giữ tọa độ cũ nếu chưa quá giới hạn (Ví dụ: đang chớp mắt, bị tay che ngang)
                    face_data["frames"][str(frame_idx)] = last_valid_box
                else:
                    # Vượt ngưỡng Hold (Ví dụ: Nhân vật bước ra khỏi khung hình) -> Reset về Box an toàn
                    face_data["frames"][str(frame_idx)] = default_box
            
            frame_idx += 1

        cap.release()
        self.detector.unload()

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(face_data, f, indent=2)
            
        print(f"[FaceManager] Đã lưu cache khuôn mặt tại: {cache_file}")
        return face_data