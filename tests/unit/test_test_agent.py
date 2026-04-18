"""Smoke tests for the Detect Agent (D7) skeleton."""

import pytest

from src.agents.test.agent import (
    TestWorkflow,
    build_test_graph,
    create_initial_state,
)


def test_detect_workflow_compiles() -> None:
    workflow = TestWorkflow()
    compiled = workflow.compile()
    assert compiled is not None


def test_build_test_graph_compiles() -> None:
    compiled = build_test_graph()
    assert compiled is not None


def test_create_initial_state_defaults() -> None:
    state = create_initial_state(project_id="00000000-0000-0000-0000-000000000001")
    assert state["project_id"] == "00000000-0000-0000-0000-000000000001"
    assert state["task_outputs"] == {}
    assert state["detect_result"] == ""
    assert state["errors"] == []


def test_workflow_metadata() -> None:
    w = TestWorkflow()
    assert w.name == "test"


@pytest.mark.asyncio
async def test_detect_workflow_runs_all_nodes() -> None:
    """Smoke test: workflow should run all stub nodes without error."""
    workflow = TestWorkflow()
    compiled = workflow.compile()
    state = create_initial_state(project_id="00000000-0000-0000-0000-000000000001")
    result = await compiled.ainvoke(state)
    # All nodes ran — stubs set detect_result
    assert result.get("detect_result") is not None
    assert isinstance(result.get("task_outputs", {}), dict)


# ─── Skill scaffold import tests ───


def test_skill_imports() -> None:
    """All Detect skill classes should be importable."""
    from src.agents.test.skills import (
        E2ETestGenerationSkill,
        SecurityScanningSkill,
        PerformanceProfilingSkill,
        AccessibilityAuditSkill,
        CoverageAnalysisSkill,
        APIContractValidationSkill,
        AcceptanceCriteriaVerificationSkill,
        RegressionDetectionSkill,
    )
    assert E2ETestGenerationSkill.name == "e2e_test_generation"
    assert SecurityScanningSkill.name == "security_scanning"
    assert PerformanceProfilingSkill.name == "performance_profiling"
    assert AccessibilityAuditSkill.name == "accessibility_audit"
    assert CoverageAnalysisSkill.name == "coverage_analysis"
    assert APIContractValidationSkill.name == "api_contract_validation"
    assert AcceptanceCriteriaVerificationSkill.name == "acceptance_criteria_verification"
    assert RegressionDetectionSkill.name == "regression_detection"


def test_task_imports() -> None:
    """All Detect task classes should be importable."""
    from src.agents.test.tasks import (
        GenerateTestSuitesTask,
        RunSecurityScanTask,
        ValidateAPIContractsTask,
        VerifyAcceptanceCriteriaTask,
        GenerateQAReportTask,
    )
    assert GenerateTestSuitesTask.name == "generate_test_suites"
    assert RunSecurityScanTask.name == "run_security_scan"
    assert ValidateAPIContractsTask.name == "validate_api_contracts"
    assert VerifyAcceptanceCriteriaTask.name == "verify_acceptance_criteria"
    assert GenerateQAReportTask.name == "generate_qa_report"
