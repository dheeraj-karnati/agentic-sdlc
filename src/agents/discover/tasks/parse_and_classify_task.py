"""ParseAndClassifyTask: classifies uploaded content and dispatches to skills.

Takes raw uploaded content (potentially multiple files concatenated),
classifies each by type, and dispatches to the appropriate extraction skill.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class InputFile(BaseModel):
    filename: str = ""
    content: str = ""


class ParseAndClassifyInput(BaseModel):
    files: list[InputFile] = Field(default_factory=list)
    raw_text: str = ""  # fallback: single text blob


class ClassifiedItem(BaseModel):
    source: str = ""  # filename or "raw_input"
    content_type: str = ""  # source_code, brd, srs, meeting_notes, schema, api_doc, manual
    language: str = ""  # for code: python, java, etc.
    content: str = ""


class ClassifiedInputs(BaseModel):
    items: list[ClassifiedItem] = Field(default_factory=list)
    classification_reasoning: str = ""


class ParseAndClassifyTask(BaseTask[ParseAndClassifyInput, ClassifiedInputs]):
    """Classifies input content by type and prepares it for skill dispatch."""

    name = "parse_and_classify"
    description = (
        "Classify uploaded files by content type (code, BRD, meeting notes, "
        "schema, manual) so they can be routed to the correct extraction skills"
    )
    input_schema = ParseAndClassifyInput
    output_schema = ClassifiedInputs
    prompt_template = """\
Classify each of the following input files/text blocks by content type.

For each input, determine:
- content_type: one of "source_code", "brd", "srs", "meeting_notes", "schema", "api_doc", "manual"
- language: if source_code, specify the programming language (python, java, javascript, etc.)
- source: the filename or "raw_input"

{raw_text}"""

    few_shot_examples = [
        {
            "input": {
                "files": [
                    {"filename": "app.py", "content": "from flask import Flask\napp = Flask(__name__)"},
                    {"filename": "requirements.docx", "content": "1. Introduction\nThe system shall provide..."},
                ],
                "raw_text": "",
            },
            "output": {
                "items": [
                    {
                        "source": "app.py",
                        "content_type": "source_code",
                        "language": "python",
                        "content": "from flask import Flask\napp = Flask(__name__)",
                    },
                    {
                        "source": "requirements.docx",
                        "content_type": "brd",
                        "language": "",
                        "content": "1. Introduction\nThe system shall provide...",
                    },
                ],
                "classification_reasoning": "app.py contains Python imports and Flask app initialization. requirements.docx follows BRD structure with numbered sections.",
            },
        },
        {
            "input": {
                "files": [],
                "raw_text": "CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));",
            },
            "output": {
                "items": [
                    {
                        "source": "raw_input",
                        "content_type": "schema",
                        "language": "sql",
                        "content": "CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));",
                    },
                ],
                "classification_reasoning": "Contains SQL DDL statement (CREATE TABLE), classified as schema.",
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return ["code_analysis", "document_extraction", "schema_analysis"]

    def validate(self, output: ClassifiedInputs) -> bool:
        """Ensure every item has a content_type and non-empty content."""
        if not output.items:
            return False
        for item in output.items:
            if not item.content_type or not item.content:
                return False
        return True

    def _render_prompt(self, input_data: ParseAndClassifyInput) -> str:
        """Override to include file previews in the prompt.

        Only shows the first 500 chars of each file for classification —
        the full content is attached by execute() after the LLM responds.
        This keeps the prompt small enough for local/small LLMs.
        """
        import json

        parts: list[str] = []

        if self.few_shot_examples:
            parts.append("## Examples of good output\n")
            for i, example in enumerate(self.few_shot_examples, 1):
                parts.append(f"### Example {i}")
                parts.append(f"**Input:** {json.dumps(example['input'], indent=2)}")
                parts.append(f"**Output:** {json.dumps(example['output'], indent=2)}")
                parts.append("")

        parts.append("## Your task\n")
        parts.append(
            "Classify each of the following input files/text blocks by content type.\n"
            "For the 'content' field in your output, just write 'see_original' — "
            "the system will attach the full content automatically.\n"
        )

        if input_data.files:
            parts.append("### Files provided:\n")
            for f in input_data.files:
                preview = f.content[:500]
                parts.append(f"**{f.filename}** (preview):")
                parts.append(f"```\n{preview}\n```\n")

        if input_data.raw_text:
            parts.append("### Raw text input (preview):\n")
            parts.append(f"```\n{input_data.raw_text[:500]}\n```")

        return "\n".join(parts)

    async def execute(
        self,
        input_data: ParseAndClassifyInput,
        *,
        llm: Any | None = None,
    ) -> ClassifiedInputs:
        """Override to attach full content after LLM classification."""
        result = await super().execute(input_data, llm=llm)

        # Build a lookup of source -> full content
        content_map: dict[str, str] = {}
        for f in input_data.files:
            content_map[f.filename] = f.content
        if input_data.raw_text:
            content_map["raw_input"] = input_data.raw_text

        # Replace placeholder content with actual content
        for item in result.items:
            if item.source in content_map:
                item.content = content_map[item.source]
            elif not item.content or item.content == "see_original":
                # Try fuzzy match on filename
                for key, val in content_map.items():
                    if key in item.source or item.source in key:
                        item.content = val
                        break

        return result
