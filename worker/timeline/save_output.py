"""TimelinePrototypeOutput → timelines / timeline_evidences DB 반영."""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from schemas.timeline_inputs import (
    TimelineEvidenceItem,
    TimelinePrototypeAiInput,
    TimelinePrototypeOutput,
)
from sqlalchemy.orm import Session

from shared.models.complaint_model import Complaint, ComplaintStep
from shared.models.timeline_model import Timeline, TimelineEvidence

# TimelineTagType (AI) → DB 문자열 (timelines JSON / API 계약)
_AI_TAG_TO_DB: dict[str, str] = {
    "repeat": "REPEAT",
    "physical": "PHYSICAL_HARM",
    "threat": "THREAT_COERCION",
    "sexual_insult": "SEXUAL_INSULT",
    "refusal": "REFUSAL_INTENT",
}


def _map_timeline_tags(tags: list[str]) -> list[str]:
    if not tags:
        return []
    return [_AI_TAG_TO_DB[t] for t in tags]


def _file_format_to_db_file_type(file_format: str) -> str:
    """timeline_inputs FileFormat → DB file_type (DOCUMENT로 묶음)."""
    if file_format in ("PDF", "HWP", "DOCX", "TXT"):
        return "DOCUMENT"
    if file_format in ("IMAGE", "AUDIO", "VIDEO"):
        return file_format
    return "ETC"


def _extract_type_and_file_format_by_evidence_id_from_input(
    ai_input: TimelinePrototypeAiInput,
) -> dict[UUID, tuple[str, str]]:
    """ai_input.evidences → evidence_id → (type, file_format)."""
    return {e.evidence_id: (e.type, cast(str, e.file_format)) for e in ai_input.evidences}


def _transform_evidence_for_timeline_json(ev: TimelineEvidenceItem) -> dict:
    """items 안 evidences: 태그 매핑 + 썸네일 등 기본값."""
    d = ev.model_dump(mode="json")
    d["tags"] = _map_timeline_tags(ev.tags)
    d["has_thumbnail"] = False
    d["thumbnail_url"] = ""
    d["duration_seconds"] = None
    d["is_ai_original"] = True
    # id 목록은 timeline_evidences 행으로만 보관, JSON에는 넣지 않음
    d.pop("referenced_evidence_ids", None)
    return d


def build_timeline_json_for_db(output: TimelinePrototypeOutput) -> dict:
    """
    model_version / evidence_results 제외. timelines.timeline_json 용 { "items": [...] }.
    """
    items: list[dict] = []
    for date_item in output.items:
        events_out: list[dict] = []
        for event in date_item.events:
            evidences_out = [_transform_evidence_for_timeline_json(ev) for ev in event.evidences]
            events_out.append({"time": event.time, "evidences": evidences_out})
        items.append({"date": date_item.date, "events": events_out})
    return {"items": items}


def _iter_all_evidence_items(output: TimelinePrototypeOutput) -> list[TimelineEvidenceItem]:
    out: list[TimelineEvidenceItem] = []
    for date_item in output.items:
        for event in date_item.events:
            out.extend(event.evidences)
    return out


def save_output(
    db: Session,
    *,
    complaint_id: UUID,
    output: TimelinePrototypeOutput,
    ai_input: TimelinePrototypeAiInput,
) -> UUID:
    """
    timelines upsert(complaint_id 기준) + timeline_evidences 전면 교체.
    referenced_evidence_ids 길이만큼 row (각 referenced_evidence_id당 1행).
    저장 후 complaint.step 을 TIMELINE 으로 설정한다.
    """
    timeline_json = build_timeline_json_for_db(output)
    type_format_by_evidence_id = _extract_type_and_file_format_by_evidence_id_from_input(ai_input)

    timeline = db.query(Timeline).filter(Timeline.complaint_id == complaint_id).one_or_none()
    if timeline is None:
        timeline = Timeline(
            id=uuid4(),
            complaint_id=complaint_id,
            timeline_json=timeline_json,
        )
        db.add(timeline)
        db.flush()
    else:
        db.query(TimelineEvidence).filter(TimelineEvidence.timeline_id == timeline.id).delete(
            synchronize_session=False
        )
        timeline.timeline_json = timeline_json
        timeline.need_timeline_regeneration = False
        timeline.need_evidence_collection_regeneration = True
        timeline.need_timeline_pdf_regeneration = True
        db.flush()

    timeline_id = timeline.id

    for ev in _iter_all_evidence_items(output):
        for ref_id in ev.referenced_evidence_ids:
            etype, ffmt = type_format_by_evidence_id[ref_id]
            db.add(
                TimelineEvidence(
                    id=uuid4(),
                    timeline_id=timeline_id,
                    timeline_evidence_id=ev.timeline_evidence_id,
                    index=ev.index,
                    referenced_evidence_id=ref_id,
                    referenced_manual_evidence_id=None,
                    is_original_evidence=True,
                    evidence_type=etype,
                    file_type=_file_format_to_db_file_type(ffmt),
                )
            )

    db.flush()

    complaint = db.get(Complaint, complaint_id)
    complaint.step = ComplaintStep.TIMELINE

    return timeline_id
