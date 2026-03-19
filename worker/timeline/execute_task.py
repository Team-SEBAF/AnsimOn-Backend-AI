import json
import logging

from sqlalchemy.orm import Session

# from shared.core.settings import settings
from worker.models import Task
from worker.timeline.ai_input_builder import build_ai_input
from worker.timeline.schemas import TimelinePrototypeOutput

logger = logging.getLogger(__name__)


def execute_timeline_task(task: Task, db: Session) -> None:
    """
    timeline 타입 태스크 실행.
    - complaint_id로 ai_input 생성
    - build_timeline_prototype 호출
    - Output DB 저장은 추후 구현
    """
    complaint_id = task.complaint_id

    ai_input = build_ai_input(db, complaint_id)
    logger.info("AI 입력 생성 완료 (task_id: %s)", task.id)
    # logger.info("AI 입력 생성 완료 (task_id: %s) ai_input=%s", task.id, ai_input)

    # from ansimon_ai.llm.openai_client import OpenAILLMClient  # noqa: E402
    from ansimon_ai.llm.mock import MockLLMClient  # noqa: E402
    from ansimon_ai.timeline import build_timeline_prototype  # noqa: E402

    logger.info("타임라인 프로토타입 실행 시작 (task_id: %s)", task.id)

    # llm_client = OpenAILLMClient(
    #     api_key=settings.OPENAI_API_KEY,
    #     model=settings.OPENAI_MODEL,
    # )
    llm_client = MockLLMClient()
    output = build_timeline_prototype(ai_input, llm_client=llm_client)

    for r in output.evidence_results:
        logger.info(
            "evidence_result: evidence_id=%s type=%s status=%s error_code=%s error_message=%s",
            r.evidence_id,
            r.type,
            r.status,
            r.error_code,
            r.error_message,
        )

    dumped = output.model_dump(mode="json")
    result = TimelinePrototypeOutput.model_validate(dumped)
    logger.info(
        "타임라인 프로토타입 완료 (complaint_id: %s): %s",
        complaint_id,
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
    )
    # TODO: output을 DB에 저장
