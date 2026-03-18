from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.base.base_response import BaseResponse, BaseSuccessResponse
from app.core.database import get_db
from app.dev.utils import _check_dev_environment, _get_dev_db_instance, _get_rds_client

router = APIRouter(
    prefix="/api/v1/dev",
    tags=["Dev (개발용)"],
)


class DevDbStatusResponse(BaseResponse):
    status: Literal["available", "unavailable"]


@router.post(
    "/db/start",
    summary="Dev DB 시작",
    description="Dev DB를 시작합니다. 대략 3~6분 소요됩니다. 시작 중에는 status API 에서 unavailable 상태로 나타날 수 있습니다.",
    response_model=BaseSuccessResponse,
)
def start_dev_db():
    _check_dev_environment()

    db = _get_dev_db_instance()
    db_id = db["DBInstanceIdentifier"]
    status = db["DBInstanceStatus"]

    if status == "stopped":
        _get_rds_client().start_db_instance(DBInstanceIdentifier=db_id)

    return BaseSuccessResponse(
        message="Dev DB 시작 요청을 전송했습니다. 대략 3~6분 소요됩니다. 시작 중에는 status API 에서 unavailable 상태로 나타날 수 있습니다.",
    )


@router.get(
    "/db/status",
    summary="Dev DB 실행 여부 조회",
    description="Dev DB가 실행 중인지 여부를 조회합니다.",
    response_model=DevDbStatusResponse,
)
def get_dev_db_status(db: Session = Depends(get_db)):
    _check_dev_environment()

    try:
        db.execute(text("SELECT 1"))  # 테이블 없이도 실행 가능
        return DevDbStatusResponse(status="available")
    except OperationalError:
        return DevDbStatusResponse(status="unavailable")


@router.post(
    "/db/stop",
    summary="Dev DB 중지",
    description="Dev DB를 중지합니다. 대략 8~15분 소요됩니다. 중지 중에는 status API 에서 available 상태로 나타날 수 있습니다.",
    response_model=BaseSuccessResponse,
)
def stop_dev_db():
    _check_dev_environment()

    db = _get_dev_db_instance()
    db_id = db["DBInstanceIdentifier"]
    status = db["DBInstanceStatus"]

    if status == "available":
        _get_rds_client().stop_db_instance(DBInstanceIdentifier=db_id)

    return BaseSuccessResponse(
        message="Dev DB 중지 요청을 전송했습니다. 대략 8~15분 소요됩니다. 중지 중에는 status API 에서 available 상태로 나타날 수 있습니다.",
    )
