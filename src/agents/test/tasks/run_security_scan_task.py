"""Run Security Scan Task — orchestrates security scanning of source code and dependencies."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class RunSecurityScanInput(BaseModel):
    """Input for security scan task."""

    source_code: str = Field(description="Source code to scan")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies to check")
    auth_design: dict = Field(default_factory=dict, description="Authentication/authorization design")


class SecurityReportOutput(BaseModel):
    """Output of the security scan task."""

    scan_result: dict = Field(default_factory=dict, description="Full scan result details")
    critical_count: int = Field(default=0, description="Number of critical vulnerabilities")
    action_required: bool = Field(default=False, description="Whether immediate action is needed")


class RunSecurityScanTask(BaseTask[RunSecurityScanInput, SecurityReportOutput]):
    """Runs security scans on source code and dependencies, evaluating auth design."""

    name: str = "run_security_scan"
    description: str = (
        "Scan source code and dependencies for security vulnerabilities "
        "and evaluate authentication design"
    )
    input_schema = RunSecurityScanInput
    output_schema = SecurityReportOutput
    prompt_template: str = ""
    few_shot_examples: list[dict[str, Any]] = []

    def get_required_skills(self) -> list[str]:
        """Return skills this task depends on."""
        return ["security_scanning"]
