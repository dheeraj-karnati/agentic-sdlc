"""Prototype Agent tasks — design interpretation, generation, deployment, feedback."""

from src.agents.prototype.tasks.deploy_preview_task import DeployPreviewTask
from src.agents.prototype.tasks.generate_prototype_task import GeneratePrototypeTask
from src.agents.prototype.tasks.interpret_design_task import InterpretDesignTask
from src.agents.prototype.tasks.process_feedback_task import ProcessFeedbackTask
from src.agents.prototype.tasks.quality_assessment_task import PrototypeQualityAssessmentTask

__all__ = [
    "DeployPreviewTask",
    "GeneratePrototypeTask",
    "InterpretDesignTask",
    "ProcessFeedbackTask",
    "PrototypeQualityAssessmentTask",
]
