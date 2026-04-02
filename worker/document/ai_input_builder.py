from __future__ import annotations

import copy
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from shared.models.timeline_model import Timeline, TimelineEvidence
from worker.tag_map import map_db_tags_to_ai

logger = logging.getLogger(__name__)

_EVIDENCE_DROP_KEYS = frozenset({"has_thumbnail", "thumbnail_url", "duration_seconds"})


def _uuid_from_json(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


def _referenced_evidence_ids_for_timeline_evidence(
    db: Session,
    *,
    timeline_id: UUID,
    timeline_evidence_id: UUID,
) -> list[str]:
    """timeline_evidences 중 AI 원본 증거만: is_original_evidence=True 인 row의 referenced_evidence_id."""
    rows = (
        db.query(TimelineEvidence.referenced_evidence_id)
        .filter(
            TimelineEvidence.timeline_id == timeline_id,
            TimelineEvidence.timeline_evidence_id == timeline_evidence_id,
            TimelineEvidence.is_original_evidence.is_(True),
        )
        .all()
    )
    out: list[str] = []
    for (ref_id,) in rows:
        if ref_id is not None:
            out.append(str(ref_id))
    return out


def _transform_evidence_for_document_input(
    db: Session,
    *,
    timeline_id: UUID,
    ev: dict[str, Any],
) -> dict[str, Any]:
    ev_out: dict[str, Any] = {
        k: copy.deepcopy(v) for k, v in ev.items() if k not in _EVIDENCE_DROP_KEYS
    }
    ev_out["tags"] = map_db_tags_to_ai([str(t) for t in ev_out["tags"]])

    te_id = _uuid_from_json(ev_out["timeline_evidence_id"])
    if ev_out.get("is_ai_original") is False:
        ev_out["referenced_evidence_ids"] = []
    else:
        ev_out["referenced_evidence_ids"] = _referenced_evidence_ids_for_timeline_evidence(
            db, timeline_id=timeline_id, timeline_evidence_id=te_id
        )
    return ev_out


def build_document_ai_input(db: Session, complaint_id: UUID) -> dict[str, Any]:
    """
    timelines.timeline_json 을 복사한 뒤 증거 단위 후처리.
    - has_thumbnail / thumbnail_url / duration_seconds 제거
    - tags: DB → AI 태그 역매핑
    - referenced_evidence_ids: is_ai_original=False 이면 []; True 이면 timeline_evidences 조회
    """
    timeline = db.query(Timeline).filter(Timeline.complaint_id == complaint_id).one_or_none()
    if not timeline:
        raise ValueError(f"timeline 없음 (complaint_id={complaint_id})")

    payload = copy.deepcopy(timeline.timeline_json)
    items = payload["items"]

    timeline_id = timeline.id
    for date_item in items:
        for event in date_item["events"]:
            for ev in event["evidences"]:
                ev = _transform_evidence_for_document_input(db, timeline_id=timeline_id, ev=ev)

    logger.info(
        "문서 AI 인풋 생성 완료 (complaint_id=%s, timeline_id=%s, items=%d)",
        complaint_id,
        timeline_id,
        len(items),
    )
    return payload
