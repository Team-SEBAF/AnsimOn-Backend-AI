import json
import os

from dotenv import find_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# find_dotenv(): cwd에서 상위로 올라가며 .env 탐색 (프로젝트 루트)
# 배포 환경에서는 ENV != local → 플랫폼 환경변수만 사용
_ENV_FILE = find_dotenv() if os.getenv("ENV", "local") == "local" else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE or None,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    env: str = Field(default="local", alias="ENV")
    # str | list → pydantic-settings 가 env 에서 json.loads 를 먼저 시도하지 않게 함 (단일 URL 문자열 허용)
    CORS_ORIGINS: str | list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    DATABASE_URL: str | None = None
    AWS_REGION: str
    AWS_PROFILE: str | None = None
    S3_BUCKET_NAME: str | None = None
    SQS_QUEUE_URL: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def _normalize_cors_origins(cls, value: str | list[str]) -> list[str]:
        """ECS: `https://a.com`, `https://a.com,https://b.com`, JSON 배열 문자열 모두 허용."""
        default = ["http://localhost:3000"]
        if isinstance(value, list):
            return [str(x) for x in value] if value else default
        s = str(value).strip()
        if not s:
            return default
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed] if parsed else default
            except json.JSONDecodeError:
                pass
        parts = [x.strip() for x in s.split(",") if x.strip()]
        return parts if parts else default


settings = Settings()
