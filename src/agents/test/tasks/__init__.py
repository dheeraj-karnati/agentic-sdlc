"""Detect agent tasks — focused QA work units combining prompts + LLM + validation."""

from src.agents.test.tasks.generate_qa_report_task import (
    GenerateQAReportInput,
    GenerateQAReportTask,
    QAReport,
)
from src.agents.test.tasks.generate_test_suites_task import (
    GenerateTestSuitesInput,
    GenerateTestSuitesTask,
    TestSuitesOutput,
)
from src.agents.test.tasks.run_security_scan_task import (
    RunSecurityScanInput,
    RunSecurityScanTask,
    SecurityReportOutput,
)
from src.agents.test.tasks.validate_api_contracts_task import (
    APIValidationOutput,
    ValidateAPIContractsInput,
    ValidateAPIContractsTask,
)
from src.agents.test.tasks.verify_acceptance_criteria_task import (
    ACReportOutput,
    VerifyAcceptanceCriteriaTask,
    VerifyACInput,
)

__all__ = [
    "GenerateQAReportInput",
    "GenerateQAReportTask",
    "QAReport",
    "GenerateTestSuitesInput",
    "GenerateTestSuitesTask",
    "TestSuitesOutput",
    "RunSecurityScanInput",
    "RunSecurityScanTask",
    "SecurityReportOutput",
    "APIValidationOutput",
    "ValidateAPIContractsInput",
    "ValidateAPIContractsTask",
    "ACReportOutput",
    "VerifyAcceptanceCriteriaTask",
    "VerifyACInput",
]
