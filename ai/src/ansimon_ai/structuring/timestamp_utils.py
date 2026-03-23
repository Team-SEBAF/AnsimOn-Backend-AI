import re
from datetime import datetime
from typing import Optional

_DATE_PATTERNS = (
    re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"),
    re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})"),
)

_TIME_PATTERN = re.compile(r"(?:(오전|오후)\s*)?(\d{1,2}):(\d{2})")

_DATETIME_PATTERNS = (
    re.compile(
        r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
        r"\s*(오전|오후)?\s*(\d{1,2}):(\d{2})"
    ),
    re.compile(
        r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})"
        r"\s+(?:(오전|오후)\s*)?(\d{1,2}):(\d{2})"
    ),
)

def _build_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
) -> datetime:
    return datetime(year, month, day, hour, minute)

def _apply_meridiem(hour: int, meridiem: Optional[str]) -> int:
    if meridiem == "오후" and hour < 12:
        return hour + 12
    if meridiem == "오전" and hour == 12:
        return 0
    return hour

def _extract_date_parts(text: str) -> Optional[tuple[int, int, int]]:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None

def _extract_time_parts(text: str) -> Optional[tuple[int, int]]:
    match = _TIME_PATTERN.search(text)
    if not match:
        return None

    meridiem = match.group(1)
    hour = int(match.group(2))
    minute = int(match.group(3))
    hour = _apply_meridiem(hour, meridiem)
    return hour, minute

def extract_timestamp(text: str, fallback: Optional[datetime] = None) -> Optional[datetime]:
    if not text:
        return fallback

    normalized = " ".join(text.split())

    for pattern in _DATETIME_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue

        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        meridiem = match.group(4)
        hour = int(match.group(5)) if match.group(5) is not None else 0
        minute = int(match.group(6)) if match.group(6) is not None else 0
        hour = _apply_meridiem(hour, meridiem)
        return _build_datetime(year, month, day, hour, minute)

    date_parts = _extract_date_parts(normalized)
    if date_parts is None:
        return fallback

    time_parts = _extract_time_parts(normalized)
    if time_parts is None:
        return _build_datetime(*date_parts)

    hour, minute = time_parts
    return _build_datetime(*date_parts, hour, minute)