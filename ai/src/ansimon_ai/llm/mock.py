import json

from .base import LLMClient

class MockLLMClient(LLMClient):
    def generate(self, messages: list[dict]) -> str:
        user_content = _extract_user_text(messages)

        if "Write the complaint document sections strictly from the provided input." in user_content:
            return json.dumps(_build_complaint_document_mock(), ensure_ascii=False)

        if "Write the damage facts statement strictly from the provided input." in user_content:
            return json.dumps(_build_damage_facts_statement_mock(), ensure_ascii=False)

        doc = {
            "evidence_metadata": {
                "value": {
                    "evidence_type": "text",
                    "source": "unknown",
                    "sources": ["unknown"],
                    "created_at": "unknown",
                },
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "parties": {
                "value": {
                    "actor": "unknown",
                    "target": "unknown",
                    "relationship": "unknown",
                },
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "period": {
                "value": "unknown",
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "frequency": {
                "value": "거의 매일",
                "confidence": "high",
                "evidence_span": "거의 매일",
                "evidence_anchor": None,
            },
            "channel": {
                "value": ["unknown"],
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "locations": {
                "value": ["unknown"],
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "action_types": {
                "value": [],
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "refusal_signal": {
                "value": "unknown",
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "threat_indicators": {
                "value": [],
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "impact_on_victim": {
                "value": [],
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "report_or_record": {
                "value": "unknown",
                "confidence": "low",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "tags": {
                "value": ["repeat"],
                "confidence": "medium",
                "evidence_span": None,
                "evidence_anchor": None,
            },
            "timeline_summary": {
                "value": {
                    "title": "반복 연락 정황",
                    "description": "반복적인 연락 또는 접근 정황이 포함된 증거입니다.",
                },
                "confidence": "medium",
                "evidence_span": None,
                "evidence_anchor": None,
            },
        }

        return json.dumps(doc, ensure_ascii=False)


def _extract_user_text(messages: list[dict]) -> str:
    texts: list[str] = []
    for message in messages:
        if message.get("role") != "user":
            continue

        content = message.get("content")
        if isinstance(content, str):
            texts.append(content)
            continue

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        texts.append(text)

    return "\n".join(texts)


def _build_complaint_document_mock() -> dict:
    return {
        "section_4_crime_facts": (
            "2026년 2월 16일 새벽 5시 30분경, 피고소인은 고소인에게 반복적인 협박성 문자메시지를 발송하였습니다. "
            "같은 날 오전 8시 30분경에는 고소인의 출근길 이동 경로를 따라오는 정황이 확인되었고, "
            "2026년 2월 18일 오후 5시경에는 퇴근길 편의점 앞에서 직접 접근을 시도하였습니다."
        ),
        "section_5_complaint_reason": (
            "고소인은 명시적으로 연락을 거부하였음에도 피고소인의 반복적인 연락과 접근이 계속되어 "
            "불안과 공포를 느끼고 있으며, 일상생활과 수면에 지장을 겪고 있어 본 고소를 제기합니다."
        ),
        "section_6_evidence_list_text": [
            "새벽 협박 문자 스크린샷 (2026.02.16)",
            "출근길 블랙박스 영상 (2026.02.16)",
            "퇴근길 접근 시도 관련 진술 (2026.02.18)",
        ],
    }


def _build_damage_facts_statement_mock() -> dict:
    return {
        "damage_facts_statement": (
            "2026년 2월 16일 새벽부터 피고소인으로부터 협박성 문자메시지를 반복적으로 받았고, "
            "같은 날 출근길에는 피고소인으로 추정되는 차량이 제 이동 경로를 따라오는 장면이 확인되었습니다. "
            "이후 2026년 2월 18일 퇴근길 편의점 앞에서 직접 접근 시도까지 있어 큰 불안과 공포를 느꼈으며, "
            "현재까지도 일상생활과 수면에 지장이 발생하고 있습니다."
        )
    }