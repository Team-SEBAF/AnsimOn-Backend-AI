from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import NAMESPACE_URL, uuid5

def _to_date_time_str(ts: Optional[datetime]) -> Tuple[str, str]:
    if ts is None:
        return "UNKNOWN", "00:00"
    return ts.strftime("%Y-%m-%d"), ts.strftime("%H:%M")

def _message_group_key(evidence: Dict[str, Any]) -> str:
    group_key = evidence.get("message_group_key") or evidence.get("thread_id")
    if group_key:
        return str(group_key)
    return str(evidence.get("evidence_id"))

def _resolve_timeline_evidence_id(ev: Dict[str, Any], key: Tuple[str, str]) -> str:
    existing = ev.get("timeline_evidence_id")
    if existing:
        return str(existing)

    return str(uuid5(NAMESPACE_URL, f"timeline-evidence::{key[0]}::{key[1]}"))

def build_timeline_event_evidences(evidences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for ev in evidences:
        ev_type = ev.get("evidence_type")
        if ev_type == "MESSAGE":
            key = ("MESSAGE", _message_group_key(ev))
        else:
            key = (str(ev_type), str(ev.get("evidence_id")))

        if key not in grouped:
            grouped[key] = {
                "timeline_evidence_id": _resolve_timeline_evidence_id(ev, key),
                "title": ev.get("title", ""),
                "description": ev.get("description", ""),
                "tags": list(ev.get("tags", [])),
                "referenced_evidence_count": 1,
            }
        else:
            grouped[key]["referenced_evidence_count"] += 1
            tag_set = set(grouped[key]["tags"]) | set(ev.get("tags", []))
            grouped[key]["tags"] = sorted(tag_set)

    sorted_items = sorted(
        grouped.values(),
        key=lambda item: (item.get("title", ""), item.get("timeline_evidence_id", "")),
    )

    for idx, item in enumerate(sorted_items, start=1):
        item["index"] = idx

    return sorted_items

def bucket_evidences_by_date_time(
    evidences: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for ev in evidences:
        date_str, time_str = _to_date_time_str(ev.get("timestamp"))
        key = (date_str, time_str)
        buckets.setdefault(key, []).append(ev)
    return buckets