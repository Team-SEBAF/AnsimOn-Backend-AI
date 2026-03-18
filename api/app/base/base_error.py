from enum import Enum

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class BaseErrorResponse(BaseModel):
    code: str = Field(
        ...,
        description="에러 코드 (프론트 분기용)",
        examples=["INVALID_REQUEST"],
    )
    message: str = Field(
        ...,
        description="에러 메시지 (사용자가 읽는 용도)",
        examples=["잘못된 요청입니다."],
    )
    debug_message: str | None = Field(
        None,
        description="디버그 메시지 (개발자가 읽는 용도)",
        examples=["잘못된 요청입니다."],
    )


class CodeException(Exception):
    """detail에 추가 필드를 넣으면 응답에 병합됨 (프론트에서 구조화된 데이터 접근용)."""

    def __init__(
        self,
        *,
        code: Enum | str,
        message: str,
        status_code: int,
        detail: dict | None = None,
        debug_message: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail or {}
        self.debug_message = debug_message


def register_exception_handlers(app):
    # Validation Error (422)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=BaseErrorResponse(
                code="VALIDATION_ERROR",
                message="요청 값이 올바르지 않습니다.",
            ).model_dump(),
        )

    # HTTPException (401, 403, 404 등)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=BaseErrorResponse(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
            ).model_dump(),
        )

    # 도메인 에러
    @app.exception_handler(CodeException)
    async def code_exception_handler(request: Request, exc: CodeException):
        content = {
            "code": exc.code.value if isinstance(exc.code, Enum) else exc.code,
            "message": exc.message,
            "debug_message": exc.debug_message,
            **exc.detail,
        }
        return JSONResponse(status_code=exc.status_code, content=content)

    # 처리되지 않은 에러
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=BaseErrorResponse(
                code="INTERNAL_SERVER_ERROR",
                message="서버 오류가 발생했습니다.",
            ).model_dump(),
        )
