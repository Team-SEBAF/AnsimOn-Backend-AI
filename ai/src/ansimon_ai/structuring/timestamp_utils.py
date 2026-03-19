import re
from datetime import datetime
from typing import Optional

def _build_datetime(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute)

def extract_timestamp(text: str, fallback: Optional[datetime] = None) -> Optional[datetime]:
    m = re.search(
        r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일(?:\s*(오전|오후)\s*(\d{1,2}):(\d{2}))?",
        text,
    )
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        meridiem = m.group(4)
        hour = int(m.group(5)) if m.group(5) is not None else 0
        minute = int(m.group(6)) if m.group(6) is not None else 0

        if meridiem == "오후" and hour < 12:
            hour += 12
        if meridiem == "오전" and hour == 12:
            hour = 0

        return _build_datetime(year, month, day, hour, minute)

    m = re.search(
        r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?",
        text,
    )
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4)) if m.group(4) is not None else 0
        minute = int(m.group(5)) if m.group(5) is not None else 0
        return _build_datetime(year, month, day, hour, minute)

    return fallback