import asyncio
import json
import time
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from shared.core.database import SessionLocal
from shared.models import Task, TaskStatus

router = APIRouter(prefix="/api/v1", tags=["SSE Progress Stream"])

# processed is None 구간: task_preparing 을 이 간격(초)으로 반복. 첫 바이트는 스트림 직후 1회 즉시 송신.
SSE_HEARTBEAT_INTERVAL_SEC = 10.0


def _sse_format(
    event: str,
    *,
    status: str | None,
    processed: int | None,
    total: int | None,
) -> str:
    payload = {"status": status, "processed": processed, "total": total}
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def _timeline_task_progress_generator(task_id: UUID):
    poll_interval = 1
    last_processed: int | None = None
    # processed 있음: 마지막 progress 송신 시각(실제 증가 또는 동일값 heartbeat)
    last_progress_emit_mono: float | None = None

    last_task_preparing_emit_mono = time.monotonic()
    yield _sse_format(
        "task_preparing",
        status=None,
        processed=None,
        total=None,
    )

    while True:
        db: Session = SessionLocal()
        task: Task | None = None
        try:
            task = db.get(Task, task_id)
            if not task:
                yield _sse_format(
                    "error",
                    status="task_not_found",
                    processed=None,
                    total=None,
                )
                break

            processed = (
                task.processed_evidence_count if task.processed_evidence_count is not None else 0
            )
            total = task.total_evidence_count if task.total_evidence_count is not None else 0

            if task.processed_evidence_count is not None and processed != last_processed:
                last_processed = processed
                yield _sse_format(
                    "progress",
                    status=task.status.value,
                    processed=processed,
                    total=total,
                )
                last_progress_emit_mono = time.monotonic()

            if task.status in (TaskStatus.DONE, TaskStatus.FAILED):
                yield _sse_format(
                    "done",
                    status=task.status.value,
                    processed=processed,
                    total=total,
                )
                break

        finally:
            db.close()

        now = time.monotonic()
        if task is not None and task.status not in (TaskStatus.DONE, TaskStatus.FAILED):
            if task.processed_evidence_count is None:
                if now - last_task_preparing_emit_mono >= SSE_HEARTBEAT_INTERVAL_SEC:
                    yield _sse_format(
                        "task_preparing",
                        status=task.status.value,
                        processed=None,
                        total=None,
                    )
                    last_task_preparing_emit_mono = now
            elif (
                last_progress_emit_mono is not None
                and now - last_progress_emit_mono >= SSE_HEARTBEAT_INTERVAL_SEC
            ):
                yield _sse_format(
                    "progress",
                    status=task.status.value,
                    processed=processed,
                    total=total,
                )
                last_progress_emit_mono = now

        await asyncio.sleep(poll_interval)


@router.get(
    "/timeline/{task_id}/progress",
    summary="타임라인 태스크 진행률 SSE",
    description="task_preparing(준비)·progress·done. payload는 status, processed, total 고정.",
)
async def timeline_task_progress_stream(task_id: UUID):
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
    finally:
        db.close()

    return StreamingResponse(
        _timeline_task_progress_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
