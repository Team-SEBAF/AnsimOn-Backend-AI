"""PostgreSQL json/jsonb는 문자열에 U+0000(NUL)을 둘 수 없음 — LLM/문서 추출 텍스트에서 제거."""

from __future__ import annotations

from typing import Any


def strip_json_null_chars(value: Any) -> Any:
    """dict/list/str 트리 전역에서 \\x00 제거. 그 외 타입은 그대로."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {k: strip_json_null_chars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_json_null_chars(v) for v in value]
    return value
