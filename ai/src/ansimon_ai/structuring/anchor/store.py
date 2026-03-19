import json
from pathlib import Path
from typing import Any, Dict, List

def collect_anchors(
    *,
    structuring_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    anchors: List[Dict[str, Any]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if "evidence_anchor" in node:
                raw_anchor = node.get("evidence_anchor")

                anchors.append(
                    {
                        "json_path": path,
                        "evidence_span": node.get("evidence_span"),
                        "evidence_anchor": (
                            None
                            if raw_anchor is None
                            else {
                                "modality": "text",
                                "start_char": raw_anchor.get("start_char"),
                                "end_char": raw_anchor.get("end_char"),
                            }
                        ),
                    }
                )

            for key, value in node.items():
                walk(value, f"{path}.{key}")

        elif isinstance(node, list):
            for idx, item in enumerate(node):
                walk(item, f"{path}[{idx}]")

    walk(structuring_result, "$")
    return anchors

def save_anchors(
    *,
    anchors: List[Dict[str, Any]],
    schema_version: str,
    input_hash: str,
    base_dir: Path = Path("data/anchors"),
) -> Path:
    out_dir = base_dir / schema_version
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{input_hash}.json"

    payload = {
        "schema_version": schema_version,
        "input_hash": input_hash,
        "anchors": anchors,
    }

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return out_path