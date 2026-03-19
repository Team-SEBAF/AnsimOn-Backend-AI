import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.core.aws import get_sqs_client
from shared.core.settings import settings
from worker.models.task_model import Task, TaskStatus

logger = logging.getLogger(__name__)


def receive_messages():
    response = get_sqs_client().receive_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=20,
    )
    return response.get("Messages", [])


def delete_message(receipt_handle):
    get_sqs_client().delete_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        ReceiptHandle=receipt_handle,
    )


def process_message(
    message: dict,
    db: Session,
    *,
    execute_task: Callable[[Task, Session], None],
):
    task_id = message["task_id"]
    task: Task | None = db.get(Task, task_id)

    if not task:
        logger.error("존재하지 않는 태스크입니다. (task_id: %s)", task_id)
        return True

    # 🔥 idempotency (중요)
    if task.status != TaskStatus.PENDING:
        logger.warning("처리 중인 혹은 처리된 태스크입니다. (task_id: %s)", task_id)
        return True

    try:
        # 1. 상태 변경 (PROCESSING)
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        # 2. AI 실행 + 결과 저장
        execute_task(task, db)  # execute_task 안에서 task.status 변경 하지 않기

        # 3. 상태 변경 (DONE)
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("태스크 완료되었습니다. (task_id: %s)", task_id)
        return True

    except Exception as e:
        logger.exception("태스크 처리 도중 에러가 발생했습니다. (task_id: %s)", task_id, e)
        db.rollback()
        task.retry_count += 1

        # 🔥 retry 3회 제한
        if task.retry_count >= 3:
            logger.error("재시도 횟수 초과. FAILED 처리합니다. (task_id: %s)", task_id)
            task.status = TaskStatus.FAILED
            db.commit()
            return True  # 더 이상 재시도 안 함 → 삭제

        else:
            logger.warning(
                "재시도 예정 (%d/3) (task_id: %s)",
                task.retry_count,
                task_id,
            )
            db.commit()
            return False  # 메시지 유지 → 재시도
