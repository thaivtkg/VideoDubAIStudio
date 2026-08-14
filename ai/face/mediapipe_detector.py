import cv2
import mediapipe as mp
from typing import List, Optional
from ai.face.base_face_detector import BaseFaceDetector, FaceBox

class MediaPipeFaceDetector(BaseFaceDetector):
    def __init__(self):
        self.detector = None

    def load(self, device: str = "cpu") -> None:
        """Nạp model MediaPipe (Tối ưu cực tốt cho CPU, không tốn VRAM)"""
        # Cấu trúc chuẩn: Gọi thẳng mp.solutions khi runtime
        self.detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1, 
            min_detection_confidence=0.5
        )

    def unload(self) -> None:
        """Đóng model và giải phóng RAM"""
        if self.detector:
            self.detector.close()
            self.detector = None

    def detect(self, frame) -> Optional[List[FaceBox]]:
        """Nhận diện khuôn mặt trong 1 frame ảnh (OpenCV format)"""
        if not self.detector:
            raise RuntimeError("Cần gọi load() trước khi detect()")

        # MediaPipe yêu cầu ảnh RGB, trong khi cv2 đọc vào là BGR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.detector.process(rgb_frame)

        if not results.detections:
            return []

        boxes = []
        ih, iw, _ = frame.shape
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            # Chuyển đổi tọa độ tương đối (0.0 - 1.0) sang pixel thực tế
            x = int(bboxC.xmin * iw)
            y = int(bboxC.ymin * ih)
            w = int(bboxC.width * iw)
            h = int(bboxC.height * ih)
            conf = detection.score[0]
            
            # Đảm bảo box không bị tràn viền (Out of bounds)
            x, y = max(0, x), max(0, y)
            w = min(w, iw - x)
            h = min(h, ih - y)
            
            boxes.append(FaceBox(x=x, y=y, width=w, height=h, confidence=conf))
            
        return boxes