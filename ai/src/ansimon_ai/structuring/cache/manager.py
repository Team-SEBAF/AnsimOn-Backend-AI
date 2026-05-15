import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import UUID

from dotenv import load_dotenv

from ansimon_ai.structuring.types import StructuringInput
from ansimon_ai.structuring.cache.hash import compute_input_hash
from ansimon_ai.structuring.versions import PROMPT_VERSION, SCHEMA_VERSION
from ansimon_ai.structuring.cache.storage import (
    load_structured_result,
    save_structured_result,
)

load_dotenv()

def _default_storage_path(schema_version: str, input_hash: str) -> Path:
    return Path("data") / "structuring" / schema_version / f"{input_hash}.json"

def get_or_create_structured_result(
    struct_input: StructuringInput,
    call_fn: Callable[[StructuringInput], dict],
    *,
    complaint_id: UUID | None = None,
    evidence_id: UUID | None = None,
    schema_version: str = SCHEMA_VERSION,
    prompt_version: str = PROMPT_VERSION,
    storage_path_fn: Callable[[str, str], Path] | None = None,
) -> dict:
    input_hash = compute_input_hash(
        struct_input,
        schema_version=schema_version,
        prompt_version=prompt_version,
        evidence_id=evidence_id,
    )

    is_local = os.getenv("ENV") == "local"

    if is_local:
        path_fn = storage_path_fn or _default_storage_path
        path = path_fn(schema_version, input_hash)
        cached = load_structured_result(path)
    else:
        from ansimon_ai.caching import load_cached_json
        cached = load_cached_json(input_hash)

    if cached is not None:
        return cached

    result = call_fn(struct_input)

    payload = {
        "_metadata": {
            "schema_version": schema_version,
            "prompt_version": prompt_version,
            "evidence_id": str(evidence_id) if evidence_id is not None else None,
            "input_hash": input_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "result": result,
    }

    if is_local:
        save_structured_result(path, payload)
    else:
        from ansimon_ai.caching import cache_json
        if complaint_id is None:
            raise ValueError("complaint_id is required")
        cache_json(input_hash, payload, complaint_id=complaint_id)

    return payload