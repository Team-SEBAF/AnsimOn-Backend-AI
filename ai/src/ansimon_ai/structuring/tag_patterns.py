from typing import Iterable, List

TAG_PATTERNS = {
    "repeat": ["여러 번", "반복", "계속", "지속적으로"],
    "physical": ["폭행", "상해", "신체", "멍", "상처", "피해", "밀쳤다", "때렸다"],
    "threat": ["죽인다", "가만 안 둘 거야", "협박", "위협", "무슨 일이 생길지 모른다", "겁을 줬다"],
    "sexual_insult": [
        "야한", "몸매", "가슴", "엉덩이", "섹시", "자세", "벗어", "만져", "키스", "자자", "잘래", "밤에 연락", "야한 사진",
        "음란", "성적", "성희롱", "성추행", "성폭력", "모욕", "변태", "야동", "야한 얘기", "야한 농담", "신체 부위", "야한 짤",
    ],
    "refusal": ["거절", "거부", "싫다", "하지 마", "그만해", "연락하지 말라", "차단"],
}

TAG_ORDER = ["repeat", "physical", "threat", "sexual_insult", "refusal"]
ALLOWED_TAGS = set(TAG_ORDER)

def normalize_tags(tags: Iterable[str]) -> List[str]:
    normalized = {tag for tag in tags if tag in ALLOWED_TAGS}
    return [tag for tag in TAG_ORDER if tag in normalized]

def extract_tags_from_structuring_input(struct_input) -> List[str]:
    tags = set()
    for seg in struct_input.segments:
        text = seg.text
        for tag, patterns in TAG_PATTERNS.items():
            if any(pat in text for pat in patterns):
                tags.add(tag)
    return normalize_tags(tags)