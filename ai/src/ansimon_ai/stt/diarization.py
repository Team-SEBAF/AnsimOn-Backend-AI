from __future__ import annotations
from pydantic import BaseModel
from .types import STTResult

class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: str

def assign_speakers_to_stt_segments(
    stt_result: STTResult,
    diarization_segments: list[DiarizationSegment],
) -> STTResult:
    if not diarization_segments:
        return stt_result

    assigned_segments = []
    for segment in stt_result.segments:
        speaker = _find_best_speaker(
            start=segment.start,
            end=segment.end,
            diarization_segments=diarization_segments,
        )
        assigned_segments.append(segment.model_copy(update={"speaker": speaker}))

    return stt_result.model_copy(update={"segments": assigned_segments})

def _find_best_speaker(
    *,
    start: float,
    end: float,
    diarization_segments: list[DiarizationSegment],
) -> str | None:
    best_speaker: str | None = None
    best_overlap = 0.0

    for diarized in diarization_segments:
        overlap = min(end, diarized.end) - max(start, diarized.start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = diarized.speaker

    return best_speaker