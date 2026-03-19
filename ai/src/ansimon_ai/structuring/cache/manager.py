from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ansimon_ai.structuring.types import StructuringInput
from ansimon_ai.structuring.cache.hash import compute_input_hash
from ansimon_ai.structuring.cache.storage import (
    load_structured_result,
    save_structured_result,
)

def _default_storage_path(schema_version: str, input_hash: str) -> Path:
    return Path("data") / "structuring" / schema_version / f"{input_hash}.json"

def get_or_create_structured_result(
    struct_input: StructuringInput,
    call_fn: Callable[[StructuringInput], dict],
    *,
    schema_version: str = "v1.3",
    prompt_version: str = "system_prompt_v0",
    storage_path_fn: Callable[[str, str], Path] | None = None,
) -> dict:
    input_hash = compute_input_hash(
        struct_input,
        schema_version=schema_version,
        prompt_version=prompt_version,
    )

    path_fn = storage_path_fn or _default_storage_path
    path = path_fn(schema_version, input_hash)

    cached = load_structured_result(path)
    if cached is not None:
        return cached

    result = call_fn(struct_input)

    payload = {
        "_metadata": {
            "schema_version": schema_version,
            "prompt_version": prompt_version,
            "input_hash": input_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "result": result,
    }

    save_structured_result(path, payload)
    return payload