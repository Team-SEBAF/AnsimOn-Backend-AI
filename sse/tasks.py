import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from shared.core.database import SessionLocal
from shared.models import Task, TaskStatus

router = APIRouter(tags=["SSE Progress Stream"])


def _sse_format(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _timeline_task_progress_generator(task_id: UUID):
    poll_interval = 1
    last_processed: int | None = None
    collecting_sent = False

    while True:
        db: Session = SessionLocal()
        try:
            task: Task | None = db.get(Task, task_id)
            if not task:
                yield _sse_format(
                    "error", {"message": f"존재하지 않는 태스크입니다. (task_id: {task_id})"}
                )
                break

            processed = (
                task.processed_evidence_count if task.processed_evidence_count is not None else 0
            )
            total = task.total_evidence_count if task.total_evidence_count is not None else 0

            if task.processed_evidence_count is None:
                if not collecting_sent:
                    collecting_sent = True
                    yield _sse_format(
                        "evidence_collecting",
                        {
                            "status": task.status.value,
                            "processed": None,
                            "total": None,
                        },
                    )

            elif processed != last_processed:
                last_processed = processed
                yield _sse_format(
                    "progress",
                    {
                        "status": task.status.value,
                        "processed": processed,
                        "total": total,
                    },
                )

            if task.status in (TaskStatus.DONE, TaskStatus.FAILED):
                yield _sse_format(
                    "done",
                    {
                        "status": task.status.value,
                        "processed": processed,
                        "total": total,
                    },
                )
                break

        finally:
            db.close()

        await asyncio.sleep(poll_interval)


@router.get(
    "/timeline/{task_id}/progress",
    summary="타임라인 태스크 진행률 SSE",
    description="processed/total 스트리밍. 완료 시 done 이벤트.",
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
