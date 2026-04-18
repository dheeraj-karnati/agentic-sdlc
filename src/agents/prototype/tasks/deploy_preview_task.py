"""DeployPreviewTask: deploys prototype code and captures screenshots."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.prototype.skills.preview_deployment_skill import (
    PreviewDeployment,
    PreviewDeploymentInput,
    PreviewDeploymentSkill,
)
from src.agents.prototype.skills.screenshot_skill import (
    ScreenshotInput,
    ScreenshotSkill,
)
from src.agents.prototype.skills.ui_generator_skill import PrototypeCode

logger = logging.getLogger(__name__)


class DeployPreviewInput(BaseModel):
    prototype_code: dict[str, Any]
    provider: str = "local_docker"
    project_name: str = "d8x-prototype"
    capture_screenshots: bool = True
    screenshot_pages: list[str] = Field(default_factory=list)


class DeployPreviewOutput(BaseModel):
    deployment: dict[str, Any] = Field(default_factory=dict)
    screenshots: list[dict[str, Any]] = Field(default_factory=list)


class DeployPreviewTask(BaseTask[DeployPreviewInput, DeployPreviewOutput]):
    """Deploys prototype and captures screenshots."""

    name = "deploy_preview"
    description = "Deploy prototype to preview URL and capture desktop/mobile screenshots"
    input_schema = DeployPreviewInput
    output_schema = DeployPreviewOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self) -> None:
        self._deploy_skill = PreviewDeploymentSkill()
        self._screenshot_skill = ScreenshotSkill()

    def get_required_skills(self) -> list[str]:
        return ["preview_deployment", "screenshot"]

    async def execute(self, input_data: DeployPreviewInput, *, llm: Any | None = None) -> DeployPreviewOutput:
        code = PrototypeCode.model_validate(input_data.prototype_code)

        # Deploy
        deployment = await self._deploy_skill.run(
            PreviewDeploymentInput(
                prototype_code=code,
                provider=input_data.provider,
                project_name=input_data.project_name,
            )
        )

        # Capture screenshots if deployment succeeded and has a URL
        screenshots: list[dict[str, Any]] = []
        if deployment.url and input_data.capture_screenshots:
            try:
                pages = input_data.screenshot_pages or ["/"]
                ss_result = await self._screenshot_skill.run(
                    ScreenshotInput(preview_url=deployment.url, pages=pages)
                )
                screenshots = [s.model_dump(mode="json") for s in ss_result.screenshots]
            except Exception as e:
                logger.warning("Screenshot capture failed: %s", e)

        return DeployPreviewOutput(
            deployment=deployment.model_dump(mode="json"),
            screenshots=screenshots,
        )
