from typing import List, Any

from ansimon_ai.structuring.types import StructuringResult
from ansimon_ai.structuring.tags.types import EvidenceTag

def _has_confidence(output_json: Any) -> bool:
    if isinstance(output_json, dict):
        for k, v in output_json.items():
            if k == "confidence":
                return True
            if _has_confidence(v):
                return True
    elif isinstance(output_json, list):
        for item in output_json:
            if _has_confidence(item):
                return True
    return False

def generate_evidence_tags(
    *,
    result: StructuringResult,
) -> List[EvidenceTag]:
    tags: List[EvidenceTag] = []

    if result.anchor_stats.matched_spans > 0:
        tags.append(
            EvidenceTag(
                tag="ANCHOR_OK",
                source="anchor",
            )
        )
    else:
        note = None
        if result.anchor_stats.unmatched_spans > 0:
            note = "no unique anchor match"

        tags.append(
            EvidenceTag(
                tag="ANCHOR_NOT_FOUND",
                source="anchor",
                note=note,
            )
        )

    if result.validation.status == "PASS":
        tags.append(
            EvidenceTag(
                tag="STRUCT_VALID",
                source="structure",
            )
        )
    else:
        tags.append(
            EvidenceTag(
                tag="STRUCT_INVALID",
                source="structure",
                note=result.validation.message,
            )
        )

    has_confidence = _has_confidence(result.output_json)

    if has_confidence:
        tags.append(
            EvidenceTag(
                tag="CONFIDENCE_PRESENT",
                source="confidence",
            )
        )

        if result.anchor_stats.matched_spans == 0:
            tags.append(
                EvidenceTag(
                    tag="CONFIDENCE_WITHOUT_ANCHOR",
                    source="confidence",
                )
            )

    return tags