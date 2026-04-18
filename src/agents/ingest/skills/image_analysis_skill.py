"""ImageAnalysisSkill: analyzes images using LLM vision capabilities."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill

logger = logging.getLogger(__name__)


class ImageAnalysisInput(BaseModel):
    image_path: str
    context: str = ""  # Hint about what the image might contain


class ImageAnalysis(BaseModel):
    description: str = ""
    extracted_text: str = ""
    identified_elements: list[str] = Field(default_factory=list)
    image_type: str = ""  # diagram, wireframe, screenshot, whiteboard, photo


class ImageAnalysisSkill(BaseSkill[ImageAnalysisInput, ImageAnalysis]):
    """Analyzes images using Claude vision or local vision model."""

    name = "image_analysis"
    description = "Analyze images to extract text, describe diagrams, identify UI elements"
    input_model = ImageAnalysisInput
    output_model = ImageAnalysis

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: ImageAnalysisInput) -> ImageAnalysis:
        path = Path(input_data.image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        # Try Claude vision
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage

            from src.config import settings

            if not settings.anthropic_api_key:
                raise ImportError("No Anthropic API key")

            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=settings.anthropic_api_key,
                max_tokens=2048,
            )

            image_data = base64.b64encode(path.read_bytes()).decode()
            suffix = path.suffix.lstrip(".").lower()
            media_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                          "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"}.get(suffix, "image/png")

            msg = HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                {"type": "text", "text": (
                    f"Analyze this image. Context: {input_data.context}\n\n"
                    "Return JSON: {\"description\": \"...\", \"extracted_text\": \"...\", "
                    "\"identified_elements\": [...], \"image_type\": \"diagram|wireframe|screenshot|whiteboard|photo\"}"
                )},
            ])

            response = await llm.ainvoke([msg])
            from src.tools.json_utils import parse_llm_json

            parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
            return ImageAnalysis.model_validate(parsed)

        except (ImportError, Exception) as e:
            logger.warning("Vision analysis unavailable (%s) — returning basic metadata", e)
            return ImageAnalysis(
                description=f"Image file: {path.name}",
                image_type="unknown",
                identified_elements=[f"File: {path.name}", f"Size: {path.stat().st_size} bytes"],
            )
