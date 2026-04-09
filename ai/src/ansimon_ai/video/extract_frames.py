from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import json

@dataclass(frozen=True)
class ExtractedVideoFrame:
    path: Path
    frame_index: int
    frame_timestamp_seconds: int

def get_video_duration_seconds(
    video_path: str | Path,
    *,
    ffprobe_binary: str = "ffprobe",
) -> float:
    input_path = Path(video_path)
    result = subprocess.run(
        [
            ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(input_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout or "{}")
    duration = payload.get("format", {}).get("duration")
    if duration is None:
        raise ValueError("Could not determine video duration.")

    return float(duration)

def extract_frames_from_video(
    video_path: str | Path,
    *,
    output_dir: str | Path,
    interval_seconds: int = 10,
    ffmpeg_binary: str = "ffmpeg",
) -> list[ExtractedVideoFrame]:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0.")

    input_path = Path(video_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    frame_pattern = target_dir / "frame_%06d.jpg"
    fps_filter = f"fps=1/{interval_seconds}"

    subprocess.run(
        [
            ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-vf",
            fps_filter,
            str(frame_pattern),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    frame_paths = sorted(target_dir.glob("frame_*.jpg"))
    if not frame_paths:
        raise ValueError("No frames were extracted from the video.")

    extracted: list[ExtractedVideoFrame] = []
    for index, frame_path in enumerate(frame_paths):
        extracted.append(
            ExtractedVideoFrame(
                path=frame_path,
                frame_index=index,
                frame_timestamp_seconds=index * interval_seconds,
            )
        )
    return extracted