"""타임라인 태그: AI(TimelineTagType 문자열) ↔ DB(timelines JSON) 문자열."""

# TimelineTagType (AI) → DB 문자열 (timelines JSON / API 계약)
AI_TAG_TO_DB: dict[str, str] = {
    "repeat": "REPEAT",
    "physical": "PHYSICAL_HARM",
    "threat": "THREAT_COERCION",
    "sexual_insult": "SEXUAL_INSULT",
    "refusal": "REFUSAL_INTENT",
}

DB_TO_AI_TAG: dict[str, str] = {
    "REPEAT": "repeat",
    "PHYSICAL_HARM": "physical",
    "THREAT_COERCION": "threat",
    "SEXUAL_INSULT": "sexual_insult",
    "REFUSAL_INTENT": "refusal",
}


def map_ai_tags_to_db(tags: list[str]) -> list[str]:
    """AI 스키마 태그 → DB에 저장되는 문자열."""
    if not tags:
        return []
    return [AI_TAG_TO_DB[t] for t in tags]


def map_db_tags_to_ai(tags: list[str]) -> list[str]:
    """DB 문자열 → AI 인풋용 태그."""
    if not tags:
        return []
    return [DB_TO_AI_TAG[t] for t in tags]
