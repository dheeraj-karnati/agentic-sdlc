"""Design Agent tasks — focused units of work for system design generation."""

from src.agents.design.tasks.analyze_requirements_task import AnalyzeRequirementsTask
from src.agents.design.tasks.design_quality_assessment_task import DesignQualityAssessmentTask
from src.agents.design.tasks.generate_api_contracts_task import GenerateAPIContractsTask
from src.agents.design.tasks.generate_architecture_task import GenerateArchitectureTask
from src.agents.design.tasks.generate_auth_model_task import GenerateAuthModelTask
from src.agents.design.tasks.generate_data_model_task import GenerateDataModelTask
from src.agents.design.tasks.generate_frontend_design_task import GenerateFrontendDesignTask

__all__ = [
    "AnalyzeRequirementsTask",
    "DesignQualityAssessmentTask",
    "GenerateAPIContractsTask",
    "GenerateArchitectureTask",
    "GenerateAuthModelTask",
    "GenerateDataModelTask",
    "GenerateFrontendDesignTask",
]
