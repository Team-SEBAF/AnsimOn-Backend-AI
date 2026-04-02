import json
import logging
import sys
import time
from functools import partial
from pathlib import Path

# ai 모듈(schemas, ansimon_ai 등) import를 위해 path 추가 (다른 import보다 먼저)
_project_root = Path(__file__).resolve().parent.parent
_ai_src = _project_root / "ai" / "src"
if _ai_src.exists():
    sys.path.insert(0, str(_ai_src))

# 다른 import 전에 로깅 설정
_root = logging.getLogger()
_root.handlers.clear()
_root.setLevel(logging.INFO)
_h = logging.StreamHandler(sys.stderr)
_h.setLevel(logging.INFO)
_h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
_root.addHandler(_h)

from shared.core.database import SessionLocal  # noqa: E402
from worker.document.execute_task import execute_document_task  # noqa: E402
from worker.sqs_utils import delete_message, process_message, receive_messages  # noqa: E402
from worker.timeline.execute_task import execute_timeline_task  # noqa: E402

logger = logging.getLogger(__name__)


def worker_loop():
    logger.info("🚀 AI Worker 시작")

    while True:
        messages = receive_messages()

        if not messages:
            time.sleep(1)
            continue

        for msg in messages:
            try:
                body = json.loads(msg["Body"])
            except json.JSONDecodeError as e:
                logger.error(
                    "잘못된 JSON 메시지 수신, 삭제함. raw=%s error=%s", msg["Body"][:200], e
                )
                delete_message(msg["ReceiptHandle"])
                continue

            db = SessionLocal()

            try:
                if body.get("type") == "timeline":
                    llm_type = body.get("llm_type", "mock")
                    execute_task = partial(execute_timeline_task, llm_type=llm_type)

                elif body.get("type") == "document":
                    execute_task = execute_document_task
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
