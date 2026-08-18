import os
import json
import hashlib
import cv2
from ai.face.mediapipe_detector import MediaPipeFaceDetector

class FaceManager:
    def __init__(self, cache_dir="cache/lipsync"):
        self.cache_dir = cache_dir # Thư mục mặc định cache/lipsync
        os.makedirs(self.cache_dir, exist_ok=True) # Tạo thư mục nếu chưa có
        self.detector = MediaPipeFaceDetector() # Khởi tạo MediaPipe
        # [UPGRADE]: Định nghĩa phiên bản Schema để kiểm soát tương thích
        self.schema_version = 1 

    def _get_video_hash(self, video_path: str) -> str:
        """Tạo mã băm độc nhất dựa trên đường dẫn và dung lượng file video"""
        file_stat = os.stat(video_path) # Đọc thông tin file
        unique_string = f"{video_path}_{file_stat.st_size}_{file_stat.st_mtime}" # Tạo chuỗi duy nhất
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest() # Mã hóa MD5

    def process_and_cache(self, video_path: str, force_recalc=False) -> dict:
        """
        Quét toàn bộ video và lưu Cache chuẩn Schema Versioning.
        Xử lý chống văng (Crash) khi mất khuôn mặt bằng Hold-Last-Box.
        """
        video_hash = self._get_video_hash(video_path) # Lấy mã hash
        cache_file = os.path.join(self.cache_dir, f"{video_hash}_faces.json") # Tạo tên file cache

        # 1. Đọc từ Cache nếu tồn tại và phải ĐÚNG Schema Version
        if os.path.exists(cache_file) and not force_recalc: # Kiểm tra file có sẵn
            try:
                with open(cache_file, 'r', encoding='utf-8') as f: # Mở file cache
                    cached_data = json.load(f) # Đọc dữ liệu JSON
                    # Nếu file cũ khác version, buộc phải quét lại để tránh lỗi
                    if cached_data.get("schema_version") == self.schema_version:
                        return cached_data
                    else:
                        print("[FaceManager] Phát hiện Cache cũ không tương thích. Khởi tạo quét lại...")
            except Exception:
                pass

        # 2. Xử lý quét khuôn mặt nếu chưa có cache
        print(f"[FaceManager] Đang khởi tạo quét khuôn mặt cho: {os.path.basename(video_path)}") # In log bắt đầu
        self.detector.load(device="cpu") # Tải model trên CPU
        
        cap = cv2.VideoCapture(video_path) # Mở video
        fps = cap.get(cv2.CAP_PROP_FPS) # Lấy khung hình/giây
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) # Lấy tổng số frame
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # [UPGRADE]: Cấu trúc JSON mới đáp ứng chuẩn Production
        face_data = {
            "schema_version": self.schema_version,
            "detector": "mediapipe",
            "video_hash": video_hash,
            "video_fps": fps, # Lưu FPS vào dict
            "width": width,
            "height": height,
            "total_frames": total_frames, # Lưu tổng số frame
            "frames": {} # Khởi tạo danh sách khung hình
        }

        frame_idx = 0 # Bộ đếm
        last_valid_box = None  # Biến lưu trữ cờ Hold-Last-Box

        while cap.isOpened(): # Vòng lặp duyệt video
            ret, frame = cap.read() # Đọc từng frame
            if not ret: # Nếu hết video
                break # Thoát vòng lặp
                
            boxes = self.detector.detect(frame) # Tìm khuôn mặt
            
            if boxes: # Nếu có khuôn mặt
                # Chỉ lưu khuôn mặt có độ tự tin cao nhất (Primary Face)
                best_face = max(boxes, key=lambda b: b.confidence) # Lấy khuôn mặt rõ nhất
                last_valid_box = [best_face.x, best_face.y, best_face.width, best_face.height] # Lấy tọa độ
                face_data["frames"][str(frame_idx)] = last_valid_box # Lưu vào frame_idx
            else:
                # [FIX LỖI FACE LOSS TỪ BẢN REVIEW]: Không thấy mặt -> Đắp tọa độ cũ vào
                if last_valid_box is not None:
                    face_data["frames"][str(frame_idx)] = last_valid_box
                else:
                    # Khung hình đầu tiên đã không có mặt -> Lấy đại vùng giữa màn hình làm box mồi
                    default_box = [width // 4, height // 4, width // 2, height // 2]
                    face_data["frames"][str(frame_idx)] = default_box
            
            frame_idx += 1 # Tăng bộ đếm

        cap.release() # Đóng video
        self.detector.unload() # Bắt buộc giải phóng RAM ngay sau khi quét xong

        # 3. Ghi ra file Cache
        with open(cache_file, 'w', encoding='utf-8') as f: # Mở file để ghi
            json.dump(face_data, f, indent=2) # Ghi dữ liệu JSON
            
        print(f"[FaceManager] Đã lưu cache khuôn mặt tại: {cache_file}") # Thông báo thành công
        return face_data # Trả về dữ liệu