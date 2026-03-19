import json
import logging
import sys
import time
from pathlib import Path

from shared.core.database import SessionLocal
from worker.sqs_utils import delete_message, process_message, receive_messages
from worker.timeline.execute_task import execute_timeline_task

# ai 모듈 import를 위해 path 추가 (main 진입 전 설정)
_project_root = Path(__file__).resolve().parent.parent
_ai_src = _project_root / "ai" / "src"
if _ai_src.exists():
    sys.path.insert(0, str(_ai_src))


logger = logging.getLogger(__name__)


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
                if body.get("type") == "timeline":
                    execute_task = execute_timeline_task

                elif body.get("type") == "document":

                    def _execute_document(task, db):
                        raise NotImplementedError("document 타입은 아직 미구현")

                    execute_task = _execute_document
                else:

                    def _unknown(task, db):
                        raise ValueError(f"알 수 없는 type: {body.get('type')}")

                    execute_task = _unknown

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
