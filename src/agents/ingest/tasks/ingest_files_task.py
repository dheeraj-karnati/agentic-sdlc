"""IngestFilesTask: dispatches files to appropriate parsing skills by extension."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.ingest.skills.code_parsing_skill import (
    CodebaseAnalysis,
    CodeParsingInput,
    CodeParsingSkill,
    SourceFile,
)
from src.agents.ingest.skills.document_parsing_skill import (
    DocumentParsingInput,
    DocumentParsingSkill,
    ParsedDocument,
)

logger = logging.getLogger(__name__)

_DOC_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".html", ".htm", ".rtf", ".csv"}
_CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cs", ".go", ".rs", ".rb",
                    ".php", ".c", ".cpp", ".h", ".hpp", ".swift", ".kt", ".scala", ".sh", ".sql"}
_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}


class UploadedFile(BaseModel):
    filename: str
    content: str = ""  # Text content (for inline text/code)
    file_path: str = ""  # Filesystem path (for binary files)


class ParsedInput(BaseModel):
    source_id: str = ""
    original_filename: str = ""
    input_type: str = ""  # document, code, audio, video, image
    parsed_text: str = ""
    parsed_data: dict[str, Any] = Field(default_factory=dict)


class IngestFilesInput(BaseModel):
    files: list[UploadedFile] = Field(default_factory=list)


class IngestedFiles(BaseModel):
    items: list[ParsedInput] = Field(default_factory=list)
    total_files: int = 0
    errors: list[str] = Field(default_factory=list)


class IngestFilesTask(BaseTask[IngestFilesInput, IngestedFiles]):
    """Dispatches uploaded files to the correct parsing skill by extension."""

    name = "ingest_files"
    description = "Route each uploaded file to the appropriate parsing skill based on file type"
    input_schema = IngestFilesInput
    output_schema = IngestedFiles
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._doc_skill = DocumentParsingSkill()
        self._code_skill = CodeParsingSkill()

    def get_required_skills(self) -> list[str]:
        return ["document_parsing", "code_parsing", "audio_transcription", "video_extraction", "image_analysis"]

    async def execute(self, input_data: IngestFilesInput, *, llm: Any | None = None) -> IngestedFiles:
        items: list[ParsedInput] = []
        errors: list[str] = []
        code_files: list[SourceFile] = []

        for i, f in enumerate(input_data.files):
            ext = ("." + f.filename.rsplit(".", 1)[-1]).lower() if "." in f.filename else ""
            source_id = f"src_{i:04d}_{f.filename}"

            try:
                if ext in _CODE_EXTENSIONS or ext == ".sql":
                    code_files.append(SourceFile(
                        file_path=f.filename,
                        content=f.content or (open(f.file_path).read() if f.file_path else ""),
                        language=ext.lstrip("."),
                    ))
                    items.append(ParsedInput(
                        source_id=source_id,
                        original_filename=f.filename,
                        input_type="code",
                        parsed_text=f.content[:10000] if f.content else "",
                    ))

                elif ext in _DOC_EXTENSIONS:
                    if f.file_path:
                        result = await self._doc_skill.run(
                            DocumentParsingInput(file_path=f.file_path, file_type=ext.lstrip("."))
                        )
                        items.append(ParsedInput(
                            source_id=source_id,
                            original_filename=f.filename,
                            input_type="document",
                            parsed_text=result.raw_text,
                            parsed_data=result.model_dump(mode="json"),
                        ))
                    elif f.content:
                        items.append(ParsedInput(
                            source_id=source_id,
                            original_filename=f.filename,
                            input_type="document",
                            parsed_text=f.content,
                        ))

                elif ext in _AUDIO_EXTENSIONS:
                    if f.file_path:
                        from src.agents.ingest.skills.audio_transcription_skill import (
                            AudioTranscriptionInput, AudioTranscriptionSkill,
                        )
                        skill = AudioTranscriptionSkill()
                        result = await skill.run(AudioTranscriptionInput(audio_file_path=f.file_path))
                        items.append(ParsedInput(
                            source_id=source_id,
                            original_filename=f.filename,
                            input_type="audio",
                            parsed_text=result.full_text,
                            parsed_data=result.model_dump(mode="json"),
                        ))

                elif ext in _VIDEO_EXTENSIONS:
                    if f.file_path:
                        from src.agents.ingest.skills.video_extraction_skill import (
                            VideoExtractionInput, VideoExtractionSkill,
                        )
                        skill = VideoExtractionSkill()
                        result = await skill.run(VideoExtractionInput(video_file_path=f.file_path))
                        items.append(ParsedInput(
                            source_id=source_id,
                            original_filename=f.filename,
                            input_type="video",
                            parsed_text=result.full_text,
                            parsed_data=result.model_dump(mode="json"),
                        ))

                elif ext in _IMAGE_EXTENSIONS:
                    if f.file_path:
                        from src.agents.ingest.skills.image_analysis_skill import (
                            ImageAnalysisInput, ImageAnalysisSkill,
                        )
                        skill = ImageAnalysisSkill()
                        result = await skill.run(ImageAnalysisInput(image_path=f.file_path))
                        items.append(ParsedInput(
                            source_id=source_id,
                            original_filename=f.filename,
                            input_type="image",
                            parsed_text=result.extracted_text,
                            parsed_data=result.model_dump(mode="json"),
                        ))

                else:
                    # Unknown type — store as raw text
                    items.append(ParsedInput(
                        source_id=source_id,
                        original_filename=f.filename,
                        input_type="unknown",
                        parsed_text=f.content[:10000] if f.content else "",
                    ))

            except Exception as e:
                logger.error("Failed to parse %s: %s", f.filename, e)
                errors.append(f"Failed to parse {f.filename}: {e}")

        # Process accumulated code files
        if code_files:
            result = await self._code_skill.run(CodeParsingInput(source_files=code_files))
            for item in items:
                if item.input_type == "code":
                    item.parsed_data = result.model_dump(mode="json")
                    break  # Attach codebase analysis to first code item

        return IngestedFiles(items=items, total_files=len(input_data.files), errors=errors)
