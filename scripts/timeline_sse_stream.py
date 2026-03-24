#!/usr/bin/env python3
"""
타임라인 생성 요청 → task_id 수신 → SSE 진행률 스트림 출력 테스트
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# --- 여기에 값 붙여넣기 (또는 환경변수로 덮어쓰기) ---
ACCESS_TOKEN = "eyJraWQiOiIxYkZPb2Q4RkV0K3hIb0c5cFdLV1h1RzF5ZEZkQzN4cVBQZlp4S2F3bmtNPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJhNDU4Y2QxYy1mMDYxLTcwNDUtNGNjNi0zOTExMzA4NWQxODciLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuYXAtbm9ydGhlYXN0LTIuYW1hem9uYXdzLmNvbVwvYXAtbm9ydGhlYXN0LTJfZ0F5UlRLMFdIIiwiY2xpZW50X2lkIjoiN29oajQ2bmxzbW1qbjk3NnBsbHBmbnAxbGEiLCJvcmlnaW5fanRpIjoiYzdkYTI5MjEtMzg4MS00ZjhmLThmZDMtNDA1YzkzNmQxNTlmIiwiZXZlbnRfaWQiOiI1MTcxOWY5OC0yNWU2LTRlMjctYmNmOC01NTQxNDIyMDNlMGMiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6ImF3cy5jb2duaXRvLnNpZ25pbi51c2VyLmFkbWluIiwiYXV0aF90aW1lIjoxNzc0MzQ0ODYyLCJleHAiOjE3NzQzNDg0NjIsImlhdCI6MTc3NDM0NDg2MiwianRpIjoiNjk1NjM1YjEtYzkzNy00NDc4LWE5NDYtNDFhMzk0YjhiNWY1IiwidXNlcm5hbWUiOiJhNDU4Y2QxYy1mMDYxLTcwNDUtNGNjNi0zOTExMzA4NWQxODcifQ.d8vwgK7CoGzTK2a4ENAD0YZLJHDXMtk4F9VRo2ZzddDA29yEKOf6ajcZ4SxazIpFlvACB2m_CV9b9Dr2lRj-RSlIN1Vfm5Up_n564bFYGFg2c91lBMM9ckmFmgVEUOcBIxahF3vSL6-y26yVFgTNIU1OfaQIccV-Z6lKUzZw_DAhdGmeX1EsAnP3C_NO7U2S5c2mPOIr0TE_bHiI3XwzD7vGhtyKWhgBcTiIcS_fm0L-LkbfpGpJkPMXjk835Yv3J5_uaq2dlxRLjAikKU3gRU-QyFllZMESVjqcIcG2vwW-doXyLRiaPTq-ii10IAcZh7rFRaPl63EkOGBrDCq2Og"
COMPLAINT_ID = "6e895470-5074-43a5-8de2-0f268eeb58ae"

BACKEND_BASE = "https://fvccs6z1m1.execute-api.ap-northeast-2.amazonaws.com/dev"
SSE_BASE = "https://j5vwnqme15.execute-api.ap-northeast-2.amazonaws.com/dev"
LLM_TYPE = "mock"


def _token() -> str:
    t = (os.environ.get("ACCESS_TOKEN") or "").strip() or ACCESS_TOKEN.strip()
    if not t:
        print(
            "ACCESS_TOKEN 이 비어 있습니다. "
            "스크립트 상단 ACCESS_TOKEN 또는 환경변수 ACCESS_TOKEN 을 설정하세요.",
            file=sys.stderr,
        )
        sys.exit(1)
    return t


def _complaint_id() -> str:
    from_cli = sys.argv[1].strip() if len(sys.argv) >= 2 else ""
    from_env = (os.environ.get("COMPLAINT_ID") or "").strip()
    from_file = COMPLAINT_ID.strip()
    cid = from_cli or from_env or from_file
    if not cid:
        print(
            "complaint_id 가 비어 있습니다. "
            "스크립트 상단 COMPLAINT_ID, 환경변수 COMPLAINT_ID, "
            f"또는 인자로 전달하세요.\n사용법: {sys.argv[0]} [<complaint_id>]",
            file=sys.stderr,
        )
        sys.exit(1)
    return cid


def request_timeline_generate(complaint_id: str, token: str) -> str:
    q = urllib.parse.urlencode({"llm_type": LLM_TYPE})
    url = f"{BACKEND_BASE.rstrip('/')}/api/v1/{complaint_id}/ai/timeline/request/generate?{q}"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {err_body or e.reason}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(body)
    task_id = data.get("task_id")
    if not task_id:
        print(f"응답에 task_id 가 없습니다: {body}", file=sys.stderr)
        sys.exit(1)
    return str(task_id)


def stream_sse_progress(task_id: str) -> None:
    url = f"{SSE_BASE.rstrip('/')}/timeline/{task_id}/progress"
    req = urllib.request.Request(url, method="GET")
    print(f"SSE 연결: {url}\n", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=None) as resp:
        while True:
            line = resp.readline()
            if not line:
                break
            sys.stdout.write(line.decode(errors="replace"))
            sys.stdout.flush()


def main() -> None:
    complaint_id = _complaint_id()
    token = _token()

    print("타임라인 생성 요청 중...", file=sys.stderr)
    task_id = request_timeline_generate(complaint_id, token)
    print(f"task_id: {task_id}\n", file=sys.stderr)

    stream_sse_progress(task_id)


if __name__ == "__main__":
    main()
