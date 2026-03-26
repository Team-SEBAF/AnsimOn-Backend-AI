import json
import logging

from schemas.timeline_inputs import TimelinePrototypeOutput
from sqlalchemy.orm import Session

from shared.models import Task
from worker.json_sanitize import strip_json_null_chars
from worker.timeline.ai_input_builder import build_ai_input
from worker.timeline.save_output import save_output

logger = logging.getLogger(__name__)


def execute_timeline_task(task: Task, db: Session, *, llm_type: str = "mock") -> None:
    # 1. AI 입력 생성
    complaint_id = task.complaint_id
    ai_input = build_ai_input(db, complaint_id)
    logger.info("AI 입력 생성 완료 (task_id: %s)", task.id)
    # logger.info("AI 입력 생성 완료 (task_id: %s) ai_input=%s", task.id, ai_input)

    # 2. LLM 클라이언트 선택
    from ansimon_ai.llm.mock import MockLLMClient  # noqa: E402
    from ansimon_ai.llm.openai_client import OpenAILLMClient  # noqa: E402
    from ansimon_ai.timeline import build_timeline_prototype  # noqa: E402

    if llm_type == "openAI":
        from shared.core.settings import settings

        llm_client = OpenAILLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )
    else:
        llm_client = MockLLMClient()

    # 3. 타임라인 프로토타입 실행
    total = len(ai_input.evidences)
    task.total_evidence_count = total
    task.processed_evidence_count = 0
    db.commit()

    def _on_progress(processed: int, total_count: int) -> None:
        task.processed_evidence_count = processed
        db.commit()
        logger.info("증거 처리 진행 (task_id: %s): (%d/%d)", task.id, processed, total_count)

    logger.info("타임라인 프로토타입 실행 시작 (task_id: %s) (llm_type: %s)", task.id, llm_type)
    output = build_timeline_prototype(
        ai_input,
        llm_client=llm_client,
        progress_callback=_on_progress,
    )

    # 4. 증거 결과 로깅
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
    dumped = strip_json_null_chars(dumped)
    result = TimelinePrototypeOutput.model_validate(dumped)
    logger.info(
        "타임라인 프로토타입 완료 (complaint_id: %s): %s",
        complaint_id,
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
    )

    timeline_id = save_output(
        db,
        complaint_id=complaint_id,
        output=result,
        ai_input=ai_input,
    )
    logger.info(
        "timelines / timeline_evidences 저장 완료 (complaint_id: %s, timeline_id: %s)",
        complaint_id,
        timeline_id,
    )

    task.result = result.model_dump(mode="json")
    logger.info("타임라인 프로토타입 결과(task.result) 저장 완료 (task_id: %s)", task.id)
