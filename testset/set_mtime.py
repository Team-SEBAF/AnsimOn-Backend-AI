"""
testset/<케이스>/ 아래 파일들의 mtime·atime을 지정 시각(Asia/Seoul)으로 맞춤.

  python3 testset/set_mtime.py case1
  python3 testset/set_mtime.py case2
  python3 testset/set_mtime.py case3
  python3 testset/set_mtime.py case4

케이스별 일정은 아래 SCHEDULE_* 로 두고, SCHEDULE_BY_CASE 에 등록한다.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Seoul")

SCHEDULE_CASE1: list[tuple[str, datetime]] = [
    ("메신저/IMG_8937.PNG", datetime(2026, 3, 1, 23, 42, tzinfo=TZ)),
    ("메신저/IMG_8938.PNG", datetime(2026, 3, 3, 0, 50, tzinfo=TZ)),
    ("메신저/IMG_8939.PNG", datetime(2026, 3, 5, 22, 21, tzinfo=TZ)),
    ("메신저/IMG_8940.PNG", datetime(2026, 3, 7, 22, 10, tzinfo=TZ)),
    ("메신저/IMG_8941.PNG", datetime(2026, 3, 10, 1, 50, tzinfo=TZ)),
    ("메신저/IMG_8942.PNG", datetime(2026, 3, 12, 16, 4, tzinfo=TZ)),
    ("메신저/IMG_8943.PNG", datetime(2026, 3, 16, 23, 55, tzinfo=TZ)),
    ("메신저/IMG_8944.PNG", datetime(2026, 3, 19, 22, 0, tzinfo=TZ)),
    ("사건일지/사건일지1.docx", datetime(2026, 3, 19, 21, 30, tzinfo=TZ)),
    ("사건일지/사건일지2.pdf", datetime(2026, 3, 20, 18, 0, tzinfo=TZ)),
    ("사건일지/사건일지3.txt", datetime(2026, 3, 21, 23, 0, tzinfo=TZ)),
    ("신고상담기록/경찰신고.pdf", datetime(2026, 3, 23, 18, 30, tzinfo=TZ)),
    ("신고상담기록/심리상담.pdf", datetime(2026, 3, 25, 19, 30, tzinfo=TZ)),
    ("통화/통화기록.png", datetime(2026, 3, 15, 23, 57, tzinfo=TZ)),
    ("통화/통화녹음.m4a", datetime(2026, 3, 22, 18, 22, tzinfo=TZ)),
    ("피해사진영상/피해사진.jpg", datetime(2026, 3, 25, 23, 0, tzinfo=TZ)),
    ("피해사진영상/피해영상.mp4", datetime(2026, 3, 26, 22, 50, tzinfo=TZ)),
]

SCHEDULE_CASE2: list[tuple[str, datetime]] = [
    ("메신저/IMG_8957.PNG", datetime(2025, 12, 10, 14, 14, tzinfo=TZ)),
    ("메신저/IMG_8958.PNG", datetime(2025, 12, 12, 14, 16, tzinfo=TZ)),
    ("메신저/IMG_8959.PNG", datetime(2025, 12, 22, 15, 0, tzinfo=TZ)),
    ("메신저/IMG_8962.PNG", datetime(2025, 12, 24, 17, 32, tzinfo=TZ)),
    ("메신저/IMG_8961.PNG", datetime(2025, 12, 29, 12, 28, tzinfo=TZ)),
    ("사건일지/사건일지1.docx", datetime(2025, 12, 16, 17, 0, tzinfo=TZ)),
    ("사건일지/사건일지2.pdf", datetime(2025, 12, 17, 12, 30, tzinfo=TZ)),
    ("사건일지/사건일지3.txt", datetime(2025, 12, 23, 18, 0, tzinfo=TZ)),
    ("신고상담기록/진료기록.docx", datetime(2026, 1, 3, 18, 30, tzinfo=TZ)),
    ("통화/통화녹음1.m4a", datetime(2025, 12, 12, 14, 32, tzinfo=TZ)),
    ("통화/통화녹음2.m4a", datetime(2025, 12, 22, 16, 17, tzinfo=TZ)),
    ("통화/부재중음성.mp3", datetime(2025, 12, 29, 12, 34, tzinfo=TZ)),
    ("피해사진영상/억지로끌려가다생긴멍.jpg", datetime(2025, 12, 26, 18, 0, tzinfo=TZ)),
    ("피해사진영상/집근처배회영상.mp4", datetime(2025, 12, 29, 12, 20, tzinfo=TZ)),
    ("피해사진영상/폭행영상.mp4", datetime(2026, 1, 3, 17, 48, tzinfo=TZ)),
]

SCHEDULE_CASE3: list[tuple[str, datetime]] = [
    ("메신저/IMG_8967.PNG", datetime(2026, 2, 14, 23, 34, tzinfo=TZ)),
    ("메신저/IMG_8968.PNG", datetime(2026, 2, 14, 23, 34, tzinfo=TZ)),
    ("메신저/IMG_8969.PNG", datetime(2026, 2, 14, 23, 34, tzinfo=TZ)),
    ("메신저/IMG_8970.PNG", datetime(2026, 2, 14, 23, 34, tzinfo=TZ)),
    ("메신저/IMG_8971.PNG", datetime(2026, 2, 17, 15, 46, tzinfo=TZ)),
    ("메신저/IMG_8972.PNG", datetime(2026, 2, 17, 15, 46, tzinfo=TZ)),
    ("메신저/IMG_8973.PNG", datetime(2026, 3, 2, 17, 29, tzinfo=TZ)),
    ("메신저/IMG_8974.PNG", datetime(2026, 3, 2, 17, 29, tzinfo=TZ)),
    ("사건일지/사건일지1.txt", datetime(2026, 2, 3, 22, 0, tzinfo=TZ)),
    ("사건일지/사건일지2.txt", datetime(2026, 2, 8, 12, 30, tzinfo=TZ)),
    ("사건일지/사건일지3.txt", datetime(2025, 2, 28, 21, 30, tzinfo=TZ)),
    ("통화/통화녹음1.m4a", datetime(2026, 2, 15, 22, 32, tzinfo=TZ)),
    ("통화/통화녹음2.m4a", datetime(2026, 2, 18, 20, 18, tzinfo=TZ)),
    ("통화/부재중음성.wav", datetime(2026, 3, 1, 1, 22, tzinfo=TZ)),
    ("피해사진영상/침입영상.mp4", datetime(2026, 3, 2, 14, 48, tzinfo=TZ)),
]

SCHEDULE_CASE4: list[tuple[str, datetime]] = [
    ("메신저/IMG_8977.PNG", datetime(2025, 4, 2, 19, 20, tzinfo=TZ)),
    ("메신저/IMG_8978.PNG", datetime(2025, 4, 4, 19, 21, tzinfo=TZ)),
    ("메신저/IMG_8979.PNG", datetime(2025, 4, 9, 15, 2, tzinfo=TZ)),
    ("메신저/IMG_8980.PNG", datetime(2025, 4, 15, 23, 42, tzinfo=TZ)),
    ("메신저/IMG_8981.PNG", datetime(2025, 5, 1, 20, 14, tzinfo=TZ)),
    ("메신저/IMG_8982.PNG", datetime(2025, 5, 7, 20, 16, tzinfo=TZ)),
    ("메신저/IMG_8983.PNG", datetime(2025, 5, 13, 14, 24, tzinfo=TZ)),
    ("메신저/IMG_8984.PNG", datetime(2025, 5, 25, 20, 39, tzinfo=TZ)),
    ("메신저/IMG_8985.PNG", datetime(2025, 6, 2, 20, 48, tzinfo=TZ)),
    ("메신저/IMG_8986.PNG", datetime(2025, 6, 5, 21, 5, tzinfo=TZ)),
    ("사건일지/사건일지1.docx", datetime(2025, 4, 7, 22, 0, tzinfo=TZ)),
    ("사건일지/사건일지2.docx", datetime(2025, 4, 18, 17, 30, tzinfo=TZ)),
    ("사건일지/사건일지3.pdf", datetime(2025, 5, 4, 20, 22, tzinfo=TZ)),
    ("사건일지/사건일지4.txt", datetime(2025, 5, 21, 12, 30, tzinfo=TZ)),
    ("통화/통화녹음1.mp3", datetime(2025, 4, 12, 19, 9, tzinfo=TZ)),
    ("통화/통화녹음2.wav", datetime(2025, 4, 22, 14, 18, tzinfo=TZ)),
    ("통화/통화기록.png", datetime(2025, 5, 10, 23, 59, tzinfo=TZ)),
    ("통화/부재중음성.mp3", datetime(2025, 5, 17, 22, 48, tzinfo=TZ)),
    ("통화/통화녹음3.m4a", datetime(2025, 6, 5, 20, 33, tzinfo=TZ)),
    ("신고상담기록/심리상담.pdf", datetime(2025, 5, 26, 18, 0, tzinfo=TZ)),
    ("신고상담기록/진료기록.pdf", datetime(2025, 5, 27, 17, 30, tzinfo=TZ)),
]

SCHEDULE_BY_CASE: dict[str, list[tuple[str, datetime]]] = {
    "case1": SCHEDULE_CASE1,
    "case2": SCHEDULE_CASE2,
    "case3": SCHEDULE_CASE3,
    "case4": SCHEDULE_CASE4,
}


def run_for_case(case: str) -> None:
    schedule = SCHEDULE_BY_CASE.get(case)
    if schedule is None:
        known = ", ".join(sorted(SCHEDULE_BY_CASE)) or "(없음)"
        raise SystemExit(f"등록되지 않은 케이스: {case!r}. 사용 가능: {known}")

    base = Path(__file__).resolve().parent / case
    if not base.is_dir():
        raise SystemExit(f"없는 폴더: {base}")

    for rel, dt in schedule:
        path = base / rel
        if not path.is_file():
            print(f"[SKIP] 파일 없음: {rel}")
            continue
        ts = dt.timestamp()
        os.utime(path, (ts, ts))
        print(f"[OK] {rel} -> {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    print()
    print("--- last_modified 확인 (한국 시간 KST) ---")
    for rel, _ in schedule:
        path = base / rel
        if not path.is_file():
            continue
        mtime = path.stat().st_mtime
        dt_kst = datetime.fromtimestamp(mtime, tz=TZ)
        print(f"{rel}  ->  {dt_kst.strftime('%Y-%m-%d %H:%M:%S')} KST")


def main() -> None:
    p = argparse.ArgumentParser(description="testset/<케이스> 파일 mtime 설정 (KST)")
    p.add_argument(
        "case",
        nargs="?",
        default="case1",
        help="testset 아래 폴더 이름 (기본: case1). SCHEDULE_BY_CASE 에 등록된 이름만 가능",
    )
    args = p.parse_args()
    run_for_case(args.case)


if __name__ == "__main__":
    main()
