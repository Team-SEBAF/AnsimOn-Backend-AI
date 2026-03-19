from pathlib import Path
import json

from ansimon_ai.structuring.types import StructuringInput

PROMPT_PATH = Path(__file__).parent / "system_prompt_v0.txt"

def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

def build_structuring_messages(struct_input: StructuringInput) -> list[dict]:
    segments_json = json.dumps(
        [seg.model_dump(mode="json") for seg in struct_input.segments],
        ensure_ascii=False,
        indent=2,
    )

    return [
        {
            "role": "system",
            "content": load_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "### INPUT TEXT (anchor base)\n\n"
                f"{struct_input.full_text}\n\n"
                "### SEGMENTS (json)\n\n"
                f"{segments_json}"
            ),
        },
    ]