from __future__ import annotations

from array import array
import io
import os
import subprocess
from typing import Callable
import warnings
import wave

from .diarization import DiarizationSegment

DEFAULT_PYANNOTE_MODEL = "pyannote/speaker-diarization-community-1"

class PyannoteDiarizer:
    def __init__(
        self,
        *,
        token: str | None = None,
        model: str | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        pipeline_factory: Callable | None = None,
        audio_loader: Callable | None = None,
    ):
        self.token = token or os.getenv("PYANNOTE_HF_TOKEN")
        if not self.token:
            raise ValueError("PYANNOTE_HF_TOKEN is required for pyannote diarization.")

        self.model = model or os.getenv("PYANNOTE_MODEL") or DEFAULT_PYANNOTE_MODEL
        self.min_speakers = _resolve_speaker_count(
            min_speakers,
            env_name="DIARIZATION_MIN_SPEAKERS",
        )
        self.max_speakers = _resolve_speaker_count(
            max_speakers,
            env_name="DIARIZATION_MAX_SPEAKERS",
        )
        self._audio_loader = audio_loader
        self._pipeline = self._build_pipeline(pipeline_factory)

    def diarize(self, audio_path: str) -> list[DiarizationSegment]:
        audio_input = self._load_audio_input(audio_path)
        try:
            diarization = self._run_pipeline(audio_input)
        except Exception as exc:
            if audio_input == audio_path:
                raise
            try:
                diarization = self._run_pipeline(audio_path)
            except Exception as fallback_exc:
                raise RuntimeError(
                    "Pyannote diarization failed. If this is a private or gated model, "
                    "check the HuggingFace token and model access approval."
                ) from fallback_exc
            else:
                return _parse_diarization_result(diarization)
            raise exc

        return _parse_diarization_result(diarization)

    def _run_pipeline(self, audio_input):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"std\(\): degrees of freedom is <= 0.*",
                category=UserWarning,
            )
            return self._pipeline(
                audio_input,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers,
            )

    def _build_pipeline(self, pipeline_factory: Callable | None):
        if pipeline_factory is not None:
            return pipeline_factory(self.model, self.token)

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"\s*torchcodec is not installed correctly.*",
                    category=UserWarning,
                )
                from pyannote.audio import Pipeline
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "pyannote.audio is required for pyannote diarization."
            ) from exc

        return Pipeline.from_pretrained(self.model, token=self.token)

    def _load_audio_input(self, audio_path: str):
        if self._audio_loader is not None:
            try:
                return self._audio_loader(audio_path)
            except Exception:
                return audio_path

        for loader in (_load_audio_with_torchaudio, _load_audio_with_ffmpeg):
            try:
                return loader(audio_path)
            except Exception:
                continue

        return audio_path

def _resolve_speaker_count(value: int | None, *, env_name: str) -> int | None:
    if value is not None:
        return value

    raw_value = os.getenv(env_name)
    if not raw_value:
        return 2

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be an integer.") from exc

def _load_audio_with_torchaudio(audio_path: str):
    import torchaudio

    waveform, sample_rate = torchaudio.load(audio_path)
    return {
        "waveform": waveform,
        "sample_rate": sample_rate,
    }

def _load_audio_with_ffmpeg(audio_path: str):
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            audio_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            "-f",
            "wav",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    )
    return _load_wav_bytes(completed.stdout)

def _load_wav_bytes(wav_bytes: bytes):
    import torch

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV audio is supported.")

    samples = array("h")
    samples.frombytes(frames)

    if channels > 1:
        samples = array("h", samples[::channels])

    waveform = torch.tensor(samples, dtype=torch.float32).unsqueeze(0) / 32768.0
    return {
        "waveform": waveform,
        "sample_rate": sample_rate,
    }

def _parse_diarization_result(diarization) -> list[DiarizationSegment]:
    annotation = (
        getattr(diarization, "exclusive_speaker_diarization", None)
        or getattr(diarization, "speaker_diarization", None)
        or diarization
    )

    segments: list[DiarizationSegment] = []
    for turn, _track, speaker in annotation.itertracks(yield_label=True):
        segments.append(
            DiarizationSegment(
                start=float(turn.start),
                end=float(turn.end),
                speaker=str(speaker),
            )
        )
    return segments