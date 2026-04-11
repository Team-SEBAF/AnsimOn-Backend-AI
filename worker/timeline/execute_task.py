import json
import logging

from schemas.timeline_inputs import TimelinePrototypeOutput
from sqlalchemy.orm import Session

from shared.core.database import SessionLocal
from shared.models import Task
from worker.json_sanitize import strip_json_null_chars
from worker.timeline.ai_input_builder import build_ai_input
from worker.timeline.save_output import save_output

logger = logging.getLogger(__name__)


def execute_timeline_task(task: Task, db: Session, *, llm_type: str = "mock") -> None:
    task_id = task.id
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

    # 3. 타임라인 AI 실행
    total = len(ai_input.evidences)
    task.total_evidence_count = total
    task.processed_evidence_count = 0
    db.commit()

    def _on_progress(processed: int, total_count: int) -> None:
        # LLM 대기 중에는 바깥 db 세션 연결이 오래 유휴 → RDS 등이 끊을 수 있음. 진행률만 짧은 세션으로 갱신.
        with SessionLocal() as progress_db:
            row = progress_db.get(Task, task_id)
            if row is not None:
                row.processed_evidence_count = processed
                progress_db.commit()
        logger.info("증거 처리 진행 (task_id: %s): (%d/%d)", task_id, processed, total_count)

    logger.info("타임라인 AI 실행 시작 (task_id: %s) (llm_type: %s)", task.id, llm_type)
    output = build_timeline_prototype(
        ai_input,
        llm_client=llm_client,
        progress_callback=_on_progress,
    )

    # 긴 LLM 동안 유휴였던 바깥 세션 연결은 끊겼을 수 있음 → 풀에서 새 연결을 쓰도록 정리 후 task 재조회
    try:
        db.rollback()
    except Exception:
        pass
    try:
        db.connection().invalidate()
    except Exception:
        pass
    db.rollback()
    db.expire_all()
    task = db.get(Task, task_id)
    if task is None:
        raise RuntimeError(f"태스크를 찾을 수 없습니다 (task_id: {task_id})")

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
        "타임라인 AI 완료 (complaint_id: %s): %s",
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
    logger.info("타임라인 AI 결과(task.result) 저장 완료 (task_id: %s)", task.id)
