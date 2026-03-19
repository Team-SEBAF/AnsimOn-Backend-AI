import json
from .base import LLMClient

class MockLLMClient(LLMClient):
    def generate(self, messages: list[dict]) -> str:
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
            "evidence_anchor": None
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
        }

        return json.dumps(doc, ensure_ascii=False)