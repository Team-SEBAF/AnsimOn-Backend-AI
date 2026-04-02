from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from shared.models import Task
from worker.document.ai_generated_stub import build_document
from worker.document.ai_input_builder import build_document_ai_input
from worker.document.save_output import save_output

logger = logging.getLogger(__name__)


def execute_document_task(task: Task, db: Session, *, message_body: dict[str, Any]) -> None:
    # 1. AI 입력 생성
    complaint_id = task.complaint_id
    ai_input = build_document_ai_input(db, complaint_id)  # noqa: F841 — 추후 ai_input 사용 시 ruff 주석 삭제
    # logger.info("AI 입력 생성 완료 (task_id: %s)", task.id)
    logger.info("AI 입력 생성 완료 (task_id: %s) ai_input=%s", task.id, ai_input)

    # 2. 도큐먼트 AI 실행
    logger.info("도큐먼트 AI 실행 시작 (task_id: %s)", task.id)
    time.sleep(10)  # TODO: 실제 AI 호출 시간을 대체하는 임시 지연
    output = build_document()
    logger.info("도큐먼트 AI 완료 (task_id: %s): %s", task.id, output)

    document_id = save_output(
        db,
        complaint_id=complaint_id,
        output=output,
        message_body=message_body,
    )
    logger.info("documents 저장 완료 (task_id: %s, document_id: %s)", task.id, document_id)

    task.result = output.model_dump(mode="json")
    logger.info("도큐먼트 AI 결과(task.result) 저장 완료 (task_id: %s)", task.id)
