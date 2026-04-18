"""VideoExtractionSkill: extracts audio and key frames from video files."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.agents.ingest.skills.audio_transcription_skill import (
    AudioTranscriptionInput,
    AudioTranscriptionSkill,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


class KeyFrame(BaseModel):
    timestamp: float = 0.0
    description: str = ""
    frame_path: str = ""


class VideoExtractionInput(BaseModel):
    video_file_path: str
    extract_keyframes: bool = False
    language: str = "en"


class VideoExtractionResult(BaseModel):
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    duration_seconds: float = 0.0
    key_frames: list[KeyFrame] = Field(default_factory=list)


class VideoExtractionSkill(BaseSkill[VideoExtractionInput, VideoExtractionResult]):
    """Extracts audio transcript and optional key frames from video files."""

    name = "video_extraction"
    description = "Extract audio transcript and key frames from video files"
    input_model = VideoExtractionInput
    output_model = VideoExtractionResult

    def __init__(self) -> None:
        self._audio_skill = AudioTranscriptionSkill()

    async def execute(self, input_data: VideoExtractionInput) -> VideoExtractionResult:
        video_path = Path(input_data.video_file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Extract audio track using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_path = tmp.name

        try:
            subprocess.run(
                ["ffmpeg", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le",
                 "-ar", "16000", "-ac", "1", audio_path, "-y"],
                capture_output=True, check=True, timeout=300,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning("ffmpeg extraction failed: %s — returning empty result", e)
            return VideoExtractionResult()

        # Transcribe audio
        transcription = await self._audio_skill.run(
            AudioTranscriptionInput(
                audio_file_path=audio_path,
                language=input_data.language,
            )
        )

        # Clean up temp file
        Path(audio_path).unlink(missing_ok=True)

        return VideoExtractionResult(
            transcript_segments=transcription.segments,
            full_text=transcription.full_text,
            duration_seconds=transcription.duration_seconds,
            key_frames=[],  # Key frame extraction is optional/future
        )
