from abc import ABC, abstractmethod
from .types import STTResult

class STTEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> STTResult:
        
        raise NotImplementedError