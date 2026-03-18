from dataclasses import dataclass

from botocore.exceptions import ClientError
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.base.base_error import CodeException
from app.core.aws import get_cognito_client

bearer_scheme = HTTPBearer()


@dataclass
class AuthUser:
    access_token: str
    user_sub: str
    email: str
    email_verified: bool
    name: str
    birthdate: str | None


def get_cognito_user_by_access_token(access_token: str) -> dict:
    cognito = get_cognito_client()

    try:
        return cognito.get_user(AccessToken=access_token)
    except ClientError as e:
        code = e.response["Error"]["Code"]

        if code == "NotAuthorizedException":
            raise CodeException(
                code="INVALID_ACCESS_TOKEN",
                message="로그인이 만료되었습니다. 잠시 후 다시 시도해 주세요.",
                debug_message="액세스 토큰이 유효하지 않거나 만료되었습니다. 로그아웃 상태가 아니라면 리프레시 토큰을 사용해 새 액세스 토큰을 발급받아 주세요.",
                status_code=401,
            )

        # 그 외 Cognito 에러는 상위에서 처리
        raise


def parse_auth_user_from_cognito(
    access_token: str,
    resp: dict,
) -> AuthUser:
    attrs = {attr["Name"]: attr["Value"] for attr in resp["UserAttributes"]}

    return AuthUser(
        access_token=access_token,
        user_sub=attrs["sub"],
        email=attrs["email"],
        email_verified=attrs["email_verified"] == "true",
        name=attrs.get("name"),
        birthdate=attrs.get("birthdate"),
    )


def fetch_auth_user_by_access_token(access_token: str) -> AuthUser:
    resp = get_cognito_user_by_access_token(access_token)
    return parse_auth_user_from_cognito(access_token, resp)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthUser:
    return fetch_auth_user_by_access_token(credentials.credentials)


__all__ = [
    "AuthUser",
    "get_current_user",
    "fetch_auth_user_by_access_token",
]
