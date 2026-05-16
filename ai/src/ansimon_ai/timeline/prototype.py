from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
import shutil
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import List, Optional, Tuple

from ansimon_ai.eval.validator_adapter_v0 import StructuringValidatorV0
from ansimon_ai.structuring.anchor.matcher import AnchorMatcher
from ansimon_ai.structuring.from_stt import build_structuring_input_from_stt
from ansimon_ai.structuring.from_text import build_structuring_input_from_text
from ansimon_ai.prompting.build_messages import (
    build_victim_image_messages,
    build_victim_video_messages,
)
from ansimon_ai.structuring.run import run_structuring_pipeline
from ansimon_ai.structuring.timestamp_utils import extract_timestamp
from ansimon_ai.structuring.types import StructuringInput
from ansimon_ai.video import extract_frames_from_video, get_video_duration_seconds

from .grouping import bucket_evidences_by_date_time, build_timeline_event_evidences
from .types import (
    EvidenceProcessingResult,
    TimelineDateItem,
    TimelineEvent,
    TimelineEvidenceItem,
    TimelinePrototypeAiInput,
    TimelinePrototypeEvidenceInput,
    TimelinePrototypeOutput,
)

DEFAULT_MODEL_VERSION = "prototype-v1"

UNSUPPORTED_TYPE_ERROR = "UNSUPPORTED_EVIDENCE_TYPE"
UNSUPPORTED_FORMAT_ERROR = "UNSUPPORTED_FILE_FORMAT"
MISSING_INPUT_ERROR = "MISSING_EVIDENCE_INPUT"
MISSING_DEPENDENCY_ERROR = "MISSING_DEPENDENCY"
FILE_READ_ERROR = "FILE_READ_ERROR"
STRUCTURING_ERROR = "STRUCTURING_ERROR"

def build_timeline_prototype(
    ai_input: TimelinePrototypeAiInput,
    *,
    llm_client,
    anchor_matcher: Optional[AnchorMatcher] = None,
    validator: Optional[StructuringValidatorV0] = None,
    stt_engine=None,
    ocr_runner=None,
    cache: Optional[object] = None,
    model_version: str = DEFAULT_MODEL_VERSION,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_callback: Optional[Callable[[], bool]] = None,
    victim_video_frame_interval_seconds: int = 3,
) -> TimelinePrototypeOutput:
    if anchor_matcher is None:
        anchor_matcher = AnchorMatcher()
    if validator is None:
        validator = StructuringValidatorV0()

    process_one = partial(
        process_single_evidence,
        llm_client=llm_client,
        anchor_matcher=anchor_matcher,
        validator=validator,
        stt_engine=stt_engine,
        ocr_runner=ocr_runner,
        cache=cache,
        victim_video_frame_interval_seconds=victim_video_frame_interval_seconds,
    )
    total = len(ai_input.evidences)
    evidence_results: List[EvidenceProcessingResult] = []

    for i, ev in enumerate(ai_input.evidences):
        if cancel_callback is not None and cancel_callback():
            break
        result = process_one(ev)
        if result is not None:
            evidence_results.append(result)
        if progress_callback is not None:
            progress_callback(i + 1, total)
            
    items = _assemble_timeline_items(evidence_results)
    return TimelinePrototypeOutput(
        items=items,
        model_version=model_version,
        evidence_results=evidence_results,
    )

def process_single_evidence(
    evidence: TimelinePrototypeEvidenceInput,
    *,
    llm_client,
    anchor_matcher: Optional[AnchorMatcher] = None,
    validator: Optional[StructuringValidatorV0] = None,
    stt_engine=None,
    ocr_runner=None,
    cache: Optional[object] = None,
    victim_video_frame_interval_seconds: int = 3,
) -> EvidenceProcessingResult:
    if evidence.type == "VICTIM":
        return _process_victim_evidence(
            evidence,
            llm_client=llm_client,
            cache=cache,
            frame_interval_seconds=victim_video_frame_interval_seconds,
        )

    if anchor_matcher is None:
        anchor_matcher = AnchorMatcher()
    if validator is None:
        validator = StructuringValidatorV0()

    temp_dir = _create_runtime_temp_dir(evidence) if evidence.file_bytes is not None else None

    try:
        struct_input, source_type = _prepare_structuring_input(
            evidence,
            stt_engine=stt_engine,
            ocr_runner=ocr_runner,
            temp_dir=temp_dir,
        )
    except NotImplementedError as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=UNSUPPORTED_FORMAT_ERROR,
            error_message=str(exc),
        )
    except ModuleNotFoundError as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="failed",
            error_code=MISSING_DEPENDENCY_ERROR,
            error_message=f"Missing dependency: {exc.name}",
        )
    except (FileNotFoundError, OSError) as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="failed",
            error_code=FILE_READ_ERROR,
            error_message=str(exc),
        )
    except ValueError as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=MISSING_INPUT_ERROR,
            error_message=str(exc),
        )
    try:
        try:
            structuring_result = run_structuring_pipeline(
                input=struct_input,
                llm_client=llm_client,
                anchor_matcher=anchor_matcher,
                validator=validator,
                evidence_id=evidence.evidence_id,
                cache=cache,
            )
        except Exception as exc:
            return EvidenceProcessingResult(
                evidence_id=evidence.evidence_id,
                type=evidence.type,
                status="failed",
                source_type=source_type,
                normalized_text=struct_input.full_text,
                error_code=STRUCTURING_ERROR,
                error_message=str(exc),
            )

        normalized_text = struct_input.full_text.strip()
        title = _build_title(evidence, structuring_result.output_json)
        description = _build_description(
            evidence,
            normalized_text,
            structuring_result.output_json,
        )
        tags = _build_tags(
            structuring_result.output_json,
            evidence=evidence,
            source_type=source_type,
            normalized_text=normalized_text,
        )
        timestamp = _extract_primary_timestamp(struct_input)
        if timestamp is None:
            timestamp = evidence.file_created_at

        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="completed",
            source_type=source_type,
            normalized_text=normalized_text,
            structured_data=structuring_result.output_json,
            timestamp=timestamp,
            title=title,
            description=description,
            tags=tags,
        )
    finally:
        if temp_dir is not None:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

def _prepare_structuring_input(
    evidence: TimelinePrototypeEvidenceInput,
    *,
    stt_engine=None,
    ocr_runner=None,
    temp_dir: Optional[Path],
) -> Tuple[StructuringInput, str]:
    if evidence.type == "INCIDENT_LOG":
        if evidence.incident_log_form is not None:
            text = _incident_log_to_text(evidence)
            struct_input = build_structuring_input_from_text(
                text,
                metadata_fallback_timestamp=_build_incident_log_form_timestamp(evidence),
            )
            form_timestamp = _build_incident_log_form_timestamp(evidence)
            if form_timestamp is not None:
                for segment in struct_input.segments:
                    segment.timestamp = form_timestamp
            return struct_input, "form"

    if evidence.extracted_text:
        return _prepare_structuring_input_from_extracted_text(evidence)

    input_path = _materialize_input_file(evidence, temp_dir=temp_dir)

    if evidence.type == "MESSAGE":
        return _prepare_message_from_file(evidence, input_path, ocr_runner=ocr_runner)

    if evidence.type == "VOICE":
        return _prepare_voice_from_file(
            evidence,
            input_path,
            stt_engine=stt_engine,
            ocr_runner=ocr_runner,
        )

    if evidence.type == "REPORT_RECORD":
        return _prepare_report_record_from_file(evidence, input_path)

    if evidence.type == "INCIDENT_LOG":
        return _prepare_incident_log_from_file(evidence, input_path)

    raise NotImplementedError(f"{evidence.type} is not supported in prototype-1.")

def _process_victim_evidence(
    evidence: TimelinePrototypeEvidenceInput,
    *,
    llm_client,
    cache: Optional[object] = None,
    frame_interval_seconds: int = 3,
) -> EvidenceProcessingResult:
    if evidence.file_format not in {"IMAGE", "VIDEO"}:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=UNSUPPORTED_FORMAT_ERROR,
            error_message="VICTIM supports IMAGE or VIDEO only at the moment.",
        )

    if evidence.file_bytes is None:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=MISSING_INPUT_ERROR,
            error_message="file_bytes is required for VICTIM IMAGE evidence.",
        )

    temp_dir = _create_runtime_temp_dir(evidence)
    try:
        cache_key = _compute_victim_cache_key(
            evidence,
            default_frame_interval_seconds=frame_interval_seconds,
        )
        cached_structured_data = cache.get(cache_key) if cache is not None else None

        if cached_structured_data is not None:
            structured_data = cached_structured_data
        elif evidence.file_format == "IMAGE":
            messages = build_victim_image_messages(
                image_bytes=evidence.file_bytes,
                file_name=evidence.file_name,
                file_format=evidence.file_format,
            )
            structured_data = json.loads(llm_client.generate(messages))
            if cache is not None:
                cache.set(cache_key, structured_data)
        else:
            input_path = _materialize_input_file(evidence, temp_dir=temp_dir)
            frames_dir = temp_dir / "frames"
            resolved_frame_interval_seconds = _resolve_victim_video_frame_interval_seconds(
                input_path,
                default_interval_seconds=frame_interval_seconds,
            )
            messages = None
            if cache_key is None:
                raise ValueError("cache_key must be available for VICTIM VIDEO.")
            frames = extract_frames_from_video(
                input_path,
                output_dir=frames_dir,
                interval_seconds=resolved_frame_interval_seconds,
            )
            messages = build_victim_video_messages(
                frames=frames,
                file_name=evidence.file_name,
            )
            structured_data = json.loads(llm_client.generate(messages))
            if cache is not None:
                cache.set(cache_key, structured_data)
    except Exception as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="failed",
            source_type="vision",
            error_code=STRUCTURING_ERROR,
            error_message=str(exc),
        )
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass

    description = _clean_victim_description(
        _build_description(evidence, "", structured_data)
    )
    normalized_text = description or (evidence.file_name or str(evidence.evidence_id))

    return EvidenceProcessingResult(
        evidence_id=evidence.evidence_id,
        type=evidence.type,
        status="completed",
        source_type="vision",
        normalized_text=normalized_text,
        structured_data=structured_data,
        timestamp=evidence.file_created_at,
        title=_build_title(evidence, structured_data),
        description=description,
        tags=_build_tags(structured_data),
    )

def _prepare_structuring_input_from_extracted_text(
    evidence: TimelinePrototypeEvidenceInput,
) -> Tuple[StructuringInput, str]:
    text = (evidence.extracted_text or "").strip()
    if not text:
        raise ValueError("extracted_text is empty.")

    if evidence.type == "INCIDENT_LOG":
        return _build_document_structuring_input(text), "document"

    if evidence.type == "REPORT_RECORD":
        return _build_document_structuring_input(text), "document"

    if evidence.type == "VOICE" and evidence.file_format == "AUDIO":
        return build_structuring_input_from_text(text), "stt"

    if evidence.type in {"MESSAGE", "VOICE"} and evidence.file_format == "IMAGE":
        return build_structuring_input_from_text(text), "ocr"

    if evidence.type == "VOICE":
        return build_structuring_input_from_text(text), "stt"

    return build_structuring_input_from_text(text), "document"

def _prepare_message_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
    *,
    ocr_runner=None,
) -> Tuple[StructuringInput, str]:
    if evidence.file_format != "IMAGE":
        raise NotImplementedError("MESSAGE supports IMAGE only in prototype-1.")

    from ansimon_ai.ocr.from_ocr import build_structuring_input_from_ocr

    ocr_result = _run_ocr(input_path, ocr_runner=ocr_runner)
    return build_structuring_input_from_ocr(ocr_result), "ocr"

def _prepare_voice_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
    *,
    stt_engine=None,
    ocr_runner=None,
) -> Tuple[StructuringInput, str]:
    if evidence.file_format == "IMAGE":
        from ansimon_ai.ocr.from_ocr import build_structuring_input_from_ocr

        ocr_result = _run_ocr(input_path, ocr_runner=ocr_runner)
        return build_structuring_input_from_ocr(ocr_result), "ocr"

    if evidence.file_format == "AUDIO":
        stt_result = _run_stt(input_path, stt_engine=stt_engine)
        return build_structuring_input_from_stt(stt_result), "stt"

    raise NotImplementedError("VOICE supports AUDIO or IMAGE only in prototype-1.")

def _prepare_report_record_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
) -> Tuple[StructuringInput, str]:
    return _prepare_document_evidence_from_file(
        evidence,
        input_path,
        unsupported_hwp_message="HWP report records are not supported yet.",
        unsupported_default_message=(
            "REPORT_RECORD supports extracted_text for all formats, and direct file "
            "handling for PDF, TXT, or DOCX only in prototype-1."
        ),
    )

def _prepare_incident_log_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
) -> Tuple[StructuringInput, str]:
    return _prepare_document_evidence_from_file(
        evidence,
        input_path,
        unsupported_hwp_message="HWP incident logs are not supported yet.",
        unsupported_default_message=(
            "INCIDENT_LOG supports incident_log_form or direct file handling for PDF, "
            "TXT, or DOCX only in prototype-1."
        ),
    )

def _prepare_document_evidence_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
    *,
    unsupported_hwp_message: str,
    unsupported_default_message: str,
) -> Tuple[StructuringInput, str]:
    if evidence.file_format == "PDF":
        from ansimon_ai.pdf.document_structuring import build_structuring_input_from_document
        from ansimon_ai.pdf.extract_text_auto import extract_text_auto

        texts = extract_text_auto(input_path)
        return build_structuring_input_from_document(texts), "document"

    if evidence.file_format == "TXT":
        text = Path(input_path).read_text(encoding="utf-8")
        return _build_document_structuring_input(text), "document"

    if evidence.file_format == "DOCX":
        from ansimon_ai.pdf.extract_text_docx import extract_text_from_docx

        text = extract_text_from_docx(input_path)
        if not text.strip():
            raise ValueError("DOCX text extraction returned empty text.")
        return _build_document_structuring_input(text), "document"

    if evidence.file_format == "HWP":
        raise NotImplementedError(unsupported_hwp_message)

    raise NotImplementedError(unsupported_default_message)

def _build_document_structuring_input(text: str) -> StructuringInput:
    from ansimon_ai.pdf.document_structuring import build_structuring_input_from_document

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text]
    return build_structuring_input_from_document(lines)

def _resolve_victim_video_frame_interval_seconds(
    input_path: str,
    *,
    default_interval_seconds: int,
) -> int:
    try:
        duration_seconds = get_video_duration_seconds(input_path)
    except Exception:
        return default_interval_seconds

    if duration_seconds <= 20:
        return 1
    return default_interval_seconds

def _compute_victim_cache_key(
    evidence: TimelinePrototypeEvidenceInput,
    *,
    default_frame_interval_seconds: int,
) -> str:
    if evidence.file_bytes is None or evidence.file_format not in {"IMAGE", "VIDEO"}:
        raise ValueError("VICTIM cache key requires IMAGE/VIDEO evidence with file_bytes.")

    file_hash = hashlib.sha256(evidence.file_bytes).hexdigest()
    payload = {
        "evidence_id": str(evidence.evidence_id),
        "type": evidence.type,
        "file_format": evidence.file_format,
        "file_hash": file_hash,
        "frame_interval_seconds": default_frame_interval_seconds,
        "prompt_version": "victim_prompt_v0",
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"victim::{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"

def _run_ocr(image_path: str, *, ocr_runner=None):
    if ocr_runner is not None:
        return ocr_runner(image_path)

    from ansimon_ai.ocr.from_ocr import ocr_image_to_result

    return ocr_image_to_result(image_path)

def _run_stt(audio_path: str, *, stt_engine=None):
    if stt_engine is not None:
        return stt_engine.transcribe(audio_path)

    from ansimon_ai.stt.whisper_stt import WhisperSTT

    return WhisperSTT().transcribe(audio_path)

def _materialize_input_file(evidence: TimelinePrototypeEvidenceInput, *, temp_dir: Path) -> str:
    if evidence.file_bytes is None:
        raise ValueError("file_bytes or extracted_text is required for this evidence.")

    file_name = _resolve_temp_file_name(evidence)
    file_path = temp_dir / file_name
    file_path.write_bytes(evidence.file_bytes)
    return str(file_path)

def _resolve_temp_file_name(evidence: TimelinePrototypeEvidenceInput) -> str:
    if evidence.file_name:
        return Path(evidence.file_name).name

    suffix = _default_suffix_for_format(evidence.file_format)
    return f"{evidence.evidence_id}{suffix}"

def _default_suffix_for_format(file_format: Optional[str]) -> str:
    mapping = {
        "IMAGE": ".jpg",
        "AUDIO": ".wav",
        "VIDEO": ".mp4",
        "PDF": ".pdf",
        "HWP": ".hwp",
        "DOCX": ".docx",
        "TXT": ".txt",
    }
    return mapping.get(file_format or "", ".bin")

def _create_runtime_temp_dir(evidence: TimelinePrototypeEvidenceInput) -> Path:
    temp_dir = Path("data") / "_timeline_runtime_tmp" / str(evidence.evidence_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def _incident_log_to_text(evidence: TimelinePrototypeEvidenceInput) -> str:
    form = evidence.incident_log_form
    assert form is not None
    return "\n".join(
        [
            f"제목: {form.title}",
            f"날짜: {form.date}",
            f"시간: {form.time}",
            f"장소: {form.place}",
            f"상황: {form.situation}",
        ]
    )

def _build_incident_log_form_timestamp(
    evidence: TimelinePrototypeEvidenceInput,
) -> Optional[datetime]:
    form = evidence.incident_log_form
    if form is None:
        return None

    date_str = form.date.strip()
    time_str = form.time.strip()
    if not date_str:
        return None

    if time_str:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(f"{date_str} {time_str}", fmt)
            except ValueError:
                pass

    for fmt in ("%Y-%m-%d",):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass

    return None

def _build_title(
    evidence: TimelinePrototypeEvidenceInput,
    structured_data: Optional[dict] = None,
) -> str:
    if evidence.type == "INCIDENT_LOG" and evidence.incident_log_form is not None:
        return evidence.incident_log_form.title

    summary = _extract_timeline_summary(structured_data)
    summary_title = summary.get("title")
    if isinstance(summary_title, str) and summary_title.strip():
        return summary_title.strip()

    mapping = {
        "MESSAGE": "메신저/문자 증거",
        "VOICE": "통화/음성 증거",
        "REPORT_RECORD": "신고/상담 기록",
        "INCIDENT_LOG": "사건 일지",
    }
    return mapping.get(evidence.type, evidence.type)

def _build_description(
    evidence: TimelinePrototypeEvidenceInput,
    normalized_text: str,
    structured_data: Optional[dict] = None,
    *,
    limit: int = 280,
) -> str:
    summary = _extract_timeline_summary(structured_data)
    summary_description = summary.get("description")
    if isinstance(summary_description, str) and summary_description.strip():
        return summary_description.strip()

    text = normalized_text.strip()
    if not text:
        fallback = evidence.file_name or str(evidence.evidence_id)
        return fallback

    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."

def _clean_victim_description(description: str) -> str:
    if not description:
        return description

    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?。！？습니다])\s+", description.strip()) if sentence.strip()]
    if len(sentences) <= 1:
        return "" if _is_incidental_hand_sentence(description) else description

    kept = [sentence for sentence in sentences if not _is_incidental_hand_sentence(sentence)]
    return " ".join(kept).strip()

def _is_incidental_hand_sentence(sentence: str) -> bool:
    if not _contains_any(sentence, ("손가락", "손")):
        return False

    if _contains_any(sentence, ("멍", "변색", "상처", "출혈", "부기", "붓", "찰과상")):
        return False

    return _contains_any(
        sentence,
        ("가리키", "짚고", "짚은", "지목", "포함", "보입니다", "나와 있습니다"),
    )

def _extract_timeline_summary(structured_data: Optional[dict]) -> dict:
    if not isinstance(structured_data, dict):
        return {}

    summary = structured_data.get("timeline_summary")
    if not isinstance(summary, dict):
        return {}

    value = summary.get("value")
    if not isinstance(value, dict):
        return {}

    return value

def _build_tags(
    structured_data: Optional[dict],
    *,
    evidence: Optional[TimelinePrototypeEvidenceInput] = None,
    source_type: Optional[str] = None,
    normalized_text: str = "",
) -> List[str]:
    if not isinstance(structured_data, dict):
        return []

    tags_field = structured_data.get("tags")
    if not isinstance(tags_field, dict):
        return []

    value = tags_field.get("value")
    if not isinstance(value, list):
        return []

    allowed = {"repeat", "physical", "threat", "sexual_insult", "refusal"}
    result: List[str] = []
    for tag in value:
        if not isinstance(tag, str) or tag not in allowed or tag in result:
            continue
        if _should_drop_defensive_stt_threat_tag(
            tag,
            evidence=evidence,
            source_type=source_type,
            normalized_text=normalized_text,
            structured_data=structured_data,
        ):
            continue
        if _should_drop_weak_sexual_insult_tag(
            tag,
            normalized_text=normalized_text,
            structured_data=structured_data,
        ):
            continue
        result.append(tag)

    if "refusal" not in result and _has_refusal_evidence(structured_data, normalized_text):
        result.append("refusal")
    return result

def _should_drop_weak_sexual_insult_tag(
    tag: str,
    *,
    normalized_text: str,
    structured_data: dict,
) -> bool:
    if tag != "sexual_insult":
        return False

    combined_text = _build_tag_context_text(structured_data, normalized_text)
    if not combined_text:
        return False

    has_sexual_context = _contains_any(
        combined_text,
        (
            "성적",
            "성희롱",
            "성추행",
            "성폭력",
            "음란",
            "야한",
            "몸매",
            "가슴",
            "엉덩이",
            "벗어",
            "만져",
            "키스",
            "자자",
            "잘래",
            "성관계",
            "섹스",
            "야동",
        ),
    )
    has_direct_insult = _contains_any(
        combined_text,
        (
            "미친",
            "병신",
            "새끼",
            "걸레",
            "창녀",
            "변태",
            "더럽",
            "꺼져",
            "모욕",
        ),
    )
    if has_sexual_context:
        return False
    if has_direct_insult:
        return _is_third_party_or_comparison_insult(combined_text)

    weak_grievance_context = _contains_any(
        combined_text,
        (
            "무시당",
            "기분 나쁘",
            "불만",
            "대우",
            "다른 사람",
            "사이가 다르",
            "관계",
            "서운",
            "비하",
        ),
    )
    return weak_grievance_context

def _is_third_party_or_comparison_insult(text: str) -> bool:
    third_party_context = _contains_any(
        text,
        (
            "특정인을 비하",
            "특정인 비하",
            "제3자",
            "다른 사람",
            "선배",
            "걔",
            "쟤",
            "그 사람",
        ),
    )
    comparison_grievance_context = _contains_any(
        text,
        (
            "무시당",
            "기분 나쁘",
            "기분 더럽",
            "불만",
            "대우",
            "사이가 다르",
            "관계",
            "서운",
            "비교",
        ),
    )
    if third_party_context and comparison_grievance_context:
        return True

    if _contains_any(
        text,
        (
            "피해자를",
            "피해자한테",
            "너는",
            "너를",
            "너한테",
            "너 같은",
            "당신",
        ),
    ):
        return False

    return _contains_any(
        text,
        (
            "무시당",
            "기분 나쁘",
            "기분 더럽",
            "불만",
            "대우",
            "다른 사람",
            "사이가 다르",
            "관계",
            "서운",
            "비하",
            "특정인",
            "제3자",
            "선배",
            "걔",
            "쟤",
            "그 사람",
        ),
    )

def _has_refusal_evidence(structured_data: dict, normalized_text: str) -> bool:
    refusal_signal = structured_data.get("refusal_signal")
    if isinstance(refusal_signal, dict) and refusal_signal.get("value") == "explicit":
        return True

    summary = _extract_timeline_summary(structured_data)
    combined_text = " ".join(
        value
        for value in (summary.get("title"), summary.get("description"))
        if isinstance(value, str)
    )
    return _contains_any(
        combined_text,
        (
            "그만해",
            "그만 하",
            "그만",
            "멈춰 달",
            "멈춰달",
            "멈춰",
            "중단 요청",
            "중단 의사",
            "중단 요구",
            "연락 중단",
            "연락을 끊",
            "연락하지 말",
            "하지 말",
            "하지마",
            "거절",
        ),
    )

def _build_tag_context_text(structured_data: dict, normalized_text: str) -> str:
    summary = _extract_timeline_summary(structured_data)
    summary_text = " ".join(
        value
        for value in (summary.get("title"), summary.get("description"))
        if isinstance(value, str)
    )
    return " ".join(
        [
            normalized_text,
            summary_text,
            *_extract_structured_list_values(structured_data, "action_types"),
            *_extract_structured_list_values(structured_data, "threat_indicators"),
            *_extract_structured_list_values(structured_data, "impact_on_victim"),
        ]
    )

def _should_drop_defensive_stt_threat_tag(
    tag: str,
    *,
    evidence: Optional[TimelinePrototypeEvidenceInput],
    source_type: Optional[str],
    normalized_text: str,
    structured_data: dict,
) -> bool:
    if tag != "threat":
        return False
    if evidence is None or evidence.type != "VOICE" or source_type != "stt":
        return False

    combined_text = " ".join(
        [
            normalized_text,
            *_extract_structured_list_values(structured_data, "threat_indicators"),
            *_extract_structured_list_values(structured_data, "action_types"),
        ]
    )
    if not combined_text:
        return False

    has_block_bypass_context = _contains_any(
        combined_text,
        (
            "차단",
            "다른 번호",
            "모르는 번호",
            "낯선 번호",
            "번호로 연락",
            "번호로 전화",
        ),
    )
    has_defensive_reporting = _contains_any(
        combined_text,
        (
            "신고",
            "고소",
            "경찰",
            "법적",
            "끝까지 간다",
            "끝까지 갈",
            "끝까지 가",
        ),
    )
    if not has_block_bypass_context or not has_defensive_reporting:
        return False

    return not _contains_direct_threat_expression(combined_text)

def _extract_structured_list_values(structured_data: dict, key: str) -> List[str]:
    field = structured_data.get(key)
    if not isinstance(field, dict):
        return []

    value = field.get("value")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []

def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)

def _contains_direct_threat_expression(text: str) -> bool:
    direct_threat_terms = (
        "죽인다",
        "죽일",
        "죽여",
        "해치",
        "뒤지게",
        "때려",
        "맞고싶",
        "찾아갈",
        "가만 안",
        "가만두지",
        "불이익",
        "보복",
    )
    return _contains_any(text, direct_threat_terms)

def _extract_primary_timestamp(struct_input: StructuringInput):
    first_timestamp = None
    for segment in struct_input.segments:
        if segment.timestamp is not None:
            if first_timestamp is None:
                first_timestamp = segment.timestamp
            if segment.timestamp.hour != 0 or segment.timestamp.minute != 0:
                return segment.timestamp

    full_text_timestamp = extract_timestamp(struct_input.full_text)
    if full_text_timestamp is not None and (
        full_text_timestamp.hour != 0 or full_text_timestamp.minute != 0
    ):
        return full_text_timestamp

    return first_timestamp or full_text_timestamp

def _assemble_timeline_items(
    evidence_results: List[EvidenceProcessingResult],
) -> List[TimelineDateItem]:
    completed = [result for result in evidence_results if result.status == "completed"]
    if not completed:
        return []

    flat_evidences = [
        {
            "evidence_id": result.evidence_id,
            "evidence_type": result.type,
            "timestamp": result.timestamp,
            "title": result.title or str(result.evidence_id),
            "description": result.description or "",
            "tags": list(result.tags),
        }
        for result in completed
    ]

    buckets = bucket_evidences_by_date_time(flat_evidences)
    by_date: dict[str, List[TimelineEvent]] = {}

    for date_str, time_str in _sorted_bucket_keys(buckets):
        grouped = build_timeline_event_evidences(buckets[(date_str, time_str)])
        event = TimelineEvent(
            time=time_str,
            evidences=[TimelineEvidenceItem(**item) for item in grouped],
        )
        by_date.setdefault(date_str, []).append(event)

    return [TimelineDateItem(date=date, events=events) for date, events in by_date.items()]

def _sorted_bucket_keys(buckets):
    return sorted(
        buckets.keys(),
        key=lambda item: (_date_sort_key(item[0]), item[1]),
    )

def _date_sort_key(date_str: str):
    if date_str == "UNKNOWN":
        return (1, date_str)
    return (0, date_str)
