import hashlib
import json
import unicodedata
from typing import Any

from ansimon_ai.structuring.types import StructuringInput

def _normalize_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return unicodedata.normalize("NFC", payload)

    if isinstance(payload, list):
        return [_normalize_payload(item) for item in payload]

    if isinstance(payload, dict):
        return {
            key: _normalize_payload(payload[key])
            for key in sorted(payload.keys())
        }

    return payload

def compute_input_hash(
    struct_input: StructuringInput,
    *,
    schema_version: str,
    prompt_version: str,
) -> str:
    # Ensure the payload is JSON-serializable (Pydantic models -> plain dicts)
    base_payload = {
        **struct_input.model_dump(),
        "schema_version": schema_version,
        "prompt_version": prompt_version,
    }

    normalized = _normalize_payload(base_payload)

    serialized = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()