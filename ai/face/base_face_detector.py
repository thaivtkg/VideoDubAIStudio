from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FaceBox:
    x: int
    y: int
    width: int
    height: int
    confidence: float

class BaseFaceDetector(ABC):

    @abstractmethod
    def load(self, device: str) -> None:
        """Nạp mô hình nhận diện khuôn mặt vào thiết bị chỉ định (GPU/CPU)."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Giải phóng hoàn toàn mô hình nhận diện khuôn mặt."""
        pass

    @abstractmethod
    def detect(self, frame) -> Optional[List[FaceBox]]:
        """
        Quét và trả về danh sách các bounding box của khuôn mặt trong frame.
        Nếu không có khuôn mặt, trả về None hoặc list rỗng để hệ thống Graceful Skip.
        """
        pass