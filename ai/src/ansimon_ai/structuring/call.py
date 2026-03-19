import json
from ansimon_ai.prompting.build_messages import build_structuring_messages
from ansimon_ai.structuring.types import StructuringInput
from ansimon_ai.llm.base import LLMClient

def call_structuring_ai(
    struct_input: StructuringInput,
    llm_client: LLMClient,
) -> dict:
    messages = build_structuring_messages(struct_input)
    raw_output = llm_client.generate(messages)

    return json.loads(raw_output)