from .types import STTResult, STTSegment
from .base import STTEngine
from .mock import MockSTT

try:
    from .whisper_stt import WhisperSTT
except ModuleNotFoundError:
    WhisperSTT = None

__all__ = [
    "STTResult",
    "STTSegment",
    "STTEngine",
    "MockSTT",
    "WhisperSTT",
]