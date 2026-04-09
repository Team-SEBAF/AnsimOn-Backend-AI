from typing import Any
from uuid import UUID

from schemas.complaint_writing import (
    ComplaintWritingAiInput,
    ComplaintWritingDateItem,
    ComplaintWritingEvent,
    ComplaintWritingStructuredContext,
    ComplaintWritingTimelineItem,
)

from ansimon_ai.timeline.types import EvidenceProcessingResult, TimelineDateItem

def build_complaint_writing_input(
    *,
    complaint_id: UUID,
    timeline_items: list[TimelineDateItem],
    evidence_results: list[EvidenceProcessingResult],
) -> ComplaintWritingAiInput:
    referenced_evidence_ids = _collect_referenced_evidence_ids(timeline_items)

    return ComplaintWritingAiInput(
        complaint_id=complaint_id,
        items=[
            ComplaintWritingDateItem(
                date=date_item.date,
                events=[
                    ComplaintWritingEvent(
                        time=event.time,
                        evidences=[
                            ComplaintWritingTimelineItem(
                                title=evidence.title,
                                description=evidence.description,
                                tags=list(evidence.tags),
                                is_ai_original=evidence.is_ai_original,
                                referenced_evidence_ids=list(
                                    evidence.referenced_evidence_ids
                                ),
                            )
                            for evidence in event.evidences
                        ],
                    )
                    for event in date_item.events
                ],
            )
            for date_item in timeline_items
        ],
        structured_contexts=[
            context
            for result in evidence_results
            if (context := _build_structured_context(result)) is not None
            and context.evidence_id in referenced_evidence_ids
        ],
    )

def _collect_referenced_evidence_ids(
    timeline_items: list[TimelineDateItem],
) -> set[UUID]:
    evidence_ids: set[UUID] = set()
    for date_item in timeline_items:
        for event in date_item.events:
            for evidence in event.evidences:
                evidence_ids.update(evidence.referenced_evidence_ids)
    return evidence_ids

def _build_structured_context(
    evidence_result: EvidenceProcessingResult,
) -> ComplaintWritingStructuredContext | None:
    if evidence_result.status != "completed" or not evidence_result.structured_data:
        return None

    structured_data = evidence_result.structured_data

    return ComplaintWritingStructuredContext(
        evidence_id=evidence_result.evidence_id,
        parties=_extract_dict_value(structured_data, "parties"),
        period=_extract_str_value(structured_data, "period"),
        frequency=_extract_str_value(structured_data, "frequency"),
        channel=_extract_list_value(structured_data, "channel"),
        locations=_extract_list_value(structured_data, "locations"),
        action_types=_extract_list_value(structured_data, "action_types"),
        refusal_signal=_extract_str_value(structured_data, "refusal_signal"),
        threat_indicators=_extract_list_value(structured_data, "threat_indicators"),
        impact_on_victim=_extract_list_value(structured_data, "impact_on_victim"),
        report_or_record=_extract_str_value(structured_data, "report_or_record"),
    )

def _extract_str_value(structured_data: dict[str, Any], key: str) -> str | None:
    value = _extract_raw_value(structured_data, key)
    if not isinstance(value, str) or value == "unknown":
        return None
    return value

def _extract_list_value(structured_data: dict[str, Any], key: str) -> list[str]:
    value = _extract_raw_value(structured_data, key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item != "unknown"]

def _extract_dict_value(
    structured_data: dict[str, Any], key: str
) -> dict[str, str] | None:
    value = _extract_raw_value(structured_data, key)
    if not isinstance(value, dict):
        return None

    cleaned = {
        sub_key: sub_value
        for sub_key, sub_value in value.items()
        if isinstance(sub_value, str) and sub_value != "unknown"
    }
    return cleaned or None

def _extract_raw_value(structured_data: dict[str, Any], key: str) -> Any:
    field = structured_data.get(key)
    if not isinstance(field, dict):
        return None
    return field.get("value")