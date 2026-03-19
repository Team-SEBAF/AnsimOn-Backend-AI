from .base import STTEngine
from .types import STTResult, STTSegment
import whisper

class WhisperSTT(STTEngine):
    def __init__(self, model_size: str = "base"):
        self.model = whisper.load_model(model_size)
        self.engine_name = f"whisper-{model_size}"

    def transcribe(self, audio_path: str) -> STTResult:
        result = self.model.transcribe(audio_path, language="ko")
        segments = [
            STTSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"]
            )
            for seg in result["segments"]
        ]
        return STTResult(
            full_text=result["text"],
            segments=segments,
            language=result.get("language", "ko"),
            engine=self.engine_name
        )