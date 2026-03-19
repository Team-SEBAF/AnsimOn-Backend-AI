import json
import logging
import time

from sqlalchemy.orm import Session

from shared.core.database import SessionLocal
from worker.models.task_model import Task
from worker.sqs_utils import delete_message, process_message, receive_messages

logger = logging.getLogger(__name__)


def execute_task(task: Task, db: Session) -> None:
    """TODO: 실제 AI 로직 구현"""
    pass


def worker_loop():
    logger.info("🚀 AI Worker 시작")

    while True:
        messages = receive_messages()

        if not messages:
            time.sleep(1)
            continue

        for msg in messages:
            body = json.loads(msg["Body"])

            db = SessionLocal()

            try:
                should_delete = process_message(
                    message=body,
                    db=db,
                    execute_task=execute_task,
                )

                if should_delete:
                    delete_message(msg["ReceiptHandle"])

            finally:
                db.close()


if __name__ == "__main__":
    worker_loop()
