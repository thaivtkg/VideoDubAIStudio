import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from .subtitle_manager import SubtitleItem



@dataclass
class ProjectData:
    project_name: str
    video_path: Optional[str] = None
    srt_path: Optional[str] = None
    subtitles: List[SubtitleItem] = None

    def __post_init__(self):
        if self.subtitles is None:
            self.subtitles = []


class ProjectManager:
    def __init__(self):
        self.current_project: Optional[ProjectData] = None
        self.save_path: Optional[str] = None

    def new_project(self, name: str):
        self.current_project = ProjectData(project_name=name)
        self.save_path = None

    def save_project(self, path: str) -> bool:
        if not self.current_project:
            return False
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.current_project), f, indent=4, ensure_ascii=False)
            self.save_path = path
            return True
        except Exception as e:
            print(f"Lỗi lưu project: {e}")
            return False

    def load_project(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct Dataclass
            subs = [SubtitleItem(**item) for item in data.get('subtitles', [])]
            self.current_project = ProjectData(
                project_name=data.get('project_name', 'Untitled'),
                video_path=data.get('video_path'),
                srt_path=data.get('srt_path'),
                subtitles=subs
            )
            self.save_path = path
            return True
        except Exception as e:
            print(f"Lỗi tải project: {e}")
            return False