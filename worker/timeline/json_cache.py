from uuid import UUID

from ansimon_ai.caching import cache_json, load_cached_json


class JsonCache:
    """get/set — 내부는 S3+DB(cache_json / load_cached_json). complaint_id는 생성 시 고정."""

    def __init__(self, complaint_id: UUID) -> None:
        self._complaint_id = complaint_id

    def get(self, key: str) -> dict | None:
        return load_cached_json(key)

    def set(self, key: str, value: dict) -> None:
        cache_json(key, value, complaint_id=self._complaint_id)
