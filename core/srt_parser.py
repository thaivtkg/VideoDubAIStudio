import re
from typing import List
from .subtitle_manager import SubtitleItem


def time_to_seconds(time_str: str) -> float:
    """Chuyển đổi chuỗi thời gian SRT (00:00:12,300) sang giây."""
    h, m, s = time_str.split(':')
    s, ms = s.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(file_path: str) -> List[SubtitleItem]:
    """Đọc file SRT và trả về danh sách SubtitleItem."""
    subtitles = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Tách các block phụ đề bằng 2 dấu xuống dòng
        blocks = re.split(r'\n\s*\n', content.strip())

        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                sub_id = int(lines[0].strip())
                time_line = lines[1].strip()
                text = '\n'.join(lines[2:]).strip()

                # Cắt chuỗi thời gian
                match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', time_line)
                if match:
                    start_time = time_to_seconds(match.group(1))
                    end_time = time_to_seconds(match.group(2))
                    subtitles.append(SubtitleItem(id=sub_id, start_time=start_time, end_time=end_time, text=text))
    except Exception as e:
        print(f"Lỗi đọc file SRT: {e}")
    return subtitles