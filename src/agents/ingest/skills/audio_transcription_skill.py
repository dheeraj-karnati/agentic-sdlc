"""AudioTranscriptionSkill: transcribes audio files with speaker segmentation."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill

logger = logging.getLogger(__name__)


class TranscriptSegment(BaseModel):
    speaker_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""
    confidence: float = 0.0


class AudioTranscriptionInput(BaseModel):
    audio_file_path: str
    language: str = "en"


class TranscriptionResult(BaseModel):
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    duration_seconds: float = 0.0
    language: str = ""


class AudioTranscriptionSkill(BaseSkill[AudioTranscriptionInput, TranscriptionResult]):
    """Transcribes audio using Whisper (local) with speaker pause detection."""

    name = "audio_transcription"
    description = "Transcribe audio files with speaker diarization via pause detection"
    input_model = AudioTranscriptionInput
    output_model = TranscriptionResult

    async def execute(self, input_data: AudioTranscriptionInput) -> TranscriptionResult:
        path = Path(input_data.audio_file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(
                str(path), language=input_data.language, verbose=False
            )
        except ImportError:
            logger.warning("whisper not installed — returning empty transcription")
            return TranscriptionResult(language=input_data.language)

        segments: list[TranscriptSegment] = []
        speaker_id = "speaker_1"
        last_end = 0.0

        for seg in result.get("segments", []):
            start = seg.get("start", 0.0)
            # Simple diarization: new speaker if gap > 2 seconds
            if start - last_end > 2.0 and segments:
                current_num = int(speaker_id.split("_")[1])
                speaker_id = f"speaker_{current_num + 1}"

            segments.append(TranscriptSegment(
                speaker_id=speaker_id,
                start_time=start,
                end_time=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
                confidence=seg.get("avg_logprob", 0.0),
            ))
            last_end = seg.get("end", 0.0)

        full_text = " ".join(s.text for s in segments)
        duration = segments[-1].end_time if segments else 0.0

        return TranscriptionResult(
            segments=segments,
            full_text=full_text,
            duration_seconds=duration,
            language=result.get("language", input_data.language),
        )
