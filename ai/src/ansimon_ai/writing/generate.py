import json

from ansimon_ai.llm.base import LLMClient
from ansimon_ai.prompting.build_messages import (
    build_complaint_document_messages,
    build_damage_facts_statement_messages,
)
from schemas.complaint_writing import (
    ComplaintDocumentOutput,
    ComplaintWritingAiInput,
    DamageFactsStatementOutput,
)

def generate_complaint_document(
    ai_input: ComplaintWritingAiInput,
    *,
    llm_client: LLMClient,
) -> ComplaintDocumentOutput:
    messages = build_complaint_document_messages(ai_input)
    raw_output = llm_client.generate(messages)
    return ComplaintDocumentOutput.model_validate(json.loads(raw_output))

def generate_damage_facts_statement(
    ai_input: ComplaintWritingAiInput,
    *,
    llm_client: LLMClient,
) -> DamageFactsStatementOutput:
    messages = build_damage_facts_statement_messages(ai_input)
    raw_output = llm_client.generate(messages)
    return DamageFactsStatementOutput.model_validate(json.loads(raw_output))