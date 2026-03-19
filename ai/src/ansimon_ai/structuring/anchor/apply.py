from copy import deepcopy
from typing import Any, Dict
import unicodedata

from ansimon_ai.structuring.anchor.matcher import AnchorMatcher, EvidenceAnchor

def apply_anchors(
    *,
    structuring_result: Dict[str, Any],
    full_text: str,
    matcher: AnchorMatcher,
) -> Dict[str, Any]:
    result = deepcopy(structuring_result)

    normalized_full_text = unicodedata.normalize("NFC", full_text)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "evidence_span" in node and node["evidence_span"]:
                anchor: EvidenceAnchor | None = matcher.match(
                    full_text=normalized_full_text,
                    evidence_span=node["evidence_span"],
                )

                if anchor is None:
                    node["evidence_anchor"] = None
                else:
                    node["evidence_anchor"] = {
                        "modality": "text",
                        "start_char": anchor.start_char,
                        "end_char": anchor.end_char,
                    }

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(result)
    return result