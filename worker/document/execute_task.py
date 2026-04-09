from __future__ import annotations

import logging
from typing import Any

from ansimon_ai.llm.mock import MockLLMClient
from ansimon_ai.llm.openai_client import OpenAILLMClient
from ansimon_ai.writing.generate import (
    generate_complaint_document,
    generate_damage_facts_statement,
)
from schemas.complaint_writing import ComplaintWritingAiInput
from sqlalchemy.orm import Session

from shared.models import Task
from worker.document.ai_input_builder import build_document_ai_input
from worker.document.save_output import save_output

logger = logging.getLogger(__name__)


def execute_document_task(
    task: Task,
    db: Session,
    *,
    message_body: dict[str, Any],
    llm_type: str = "mock",
) -> None:
    # 1. AI 입력 생성
    complaint_id = task.complaint_id
    ai_input = ComplaintWritingAiInput.model_validate(build_document_ai_input(db, complaint_id))
    logger.info("AI 입력 생성 완료 (task_id: %s)", task.id)
    # logger.info("AI 입력 생성 완료 (task_id: %s) ai_input=%s", task.id, ai_input)

    if llm_type == "openAI":
        from shared.core.settings import settings

        llm_client = OpenAILLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )
    else:
        llm_client = MockLLMClient()

    # 2. 도큐먼트 AI 실행
    logger.info("도큐먼트 AI 실행 시작 (task_id: %s)", task.id)
    complaint_out = generate_complaint_document(ai_input, llm_client=llm_client)
    statement_out = generate_damage_facts_statement(ai_input, llm_client=llm_client)
    output = {
        **complaint_out.model_dump(mode="json"),
        **statement_out.model_dump(mode="json"),
    }
    logger.info("도큐먼트 AI 완료 (task_id: %s): %s", task.id, output)

    document_id = save_output(
        db,
        complaint_id=complaint_id,
        output=output,
        message_body=message_body,
    )
    logger.info("documents 저장 완료 (task_id: %s, document_id: %s)", task.id, document_id)

    task.result = output
    logger.info("도큐먼트 AI 결과(task.result) 저장 완료 (task_id: %s)", task.id)
