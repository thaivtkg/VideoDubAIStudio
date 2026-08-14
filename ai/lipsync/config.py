from dataclasses import dataclass

@dataclass
class LipSyncConfig:
    device: str = "auto"
    use_fp16: bool = True
    quality: str = "balanced"
    face_size: int = 256
    batch_size: int = 1

@dataclass
class LipSyncResult:
    output_path: str
    duration: float
    frames_processed: int
    faces_detected: int