"""Unit tests for the Prototype Agent (D4) — Workflow → Task → Skill."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.prototype.agent import (
    PrototypeWorkflow,
    build_prototype_graph,
    create_initial_state,
    quality_gate,
)
from src.agents.prototype.skills.design_interpreter_skill import (
    DesignInterpreterInput,
    DesignInterpreterSkill,
    PrototypeSpec,
)
from src.agents.prototype.skills.feedback_analyzer_skill import (
    FeedbackAnalysis,
    FeedbackAnalysisInput,
    FeedbackAnalyzerSkill,
)
from src.agents.prototype.skills.preview_deployment_skill import (
    LocalDockerProvider,
    PreviewDeployment,
    PreviewProvider,
    S3StaticProvider,
    VercelProvider,
    NetlifyProvider,
    PROVIDERS,
    get_provider,
)
from src.agents.prototype.skills.prototype_validator_skill import (
    PrototypeValidatorInput,
    PrototypeValidatorSkill,
    ValidationResult,
)
from src.agents.prototype.skills.ui_generator_skill import PrototypeCode


def _mock_llm(content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return llm


# ─── Sample Data ───

SAMPLE_SPEC = {
    "pages": [
        {"route": "/dashboard", "title": "Dashboard", "components": ["StatsCard", "OrderTable"],
         "layout": "default", "auth_required": True, "required_roles": ["admin", "manager"]},
        {"route": "/products", "title": "Products", "components": ["ProductTable"],
         "layout": "default", "auth_required": True, "required_roles": ["admin"]},
    ],
    "components": [{"name": "StatsCard", "type": "card", "props": [], "data_source": "/api/stats", "children": []}],
    "mock_data_models": [{"entity_name": "Product", "fields": [{"name": "name", "type": "string"}], "sample_count": 5, "sample_data": []}],
    "api_mocks": [{"method": "GET", "path": "/api/products", "response_schema": {}, "sample_response": {}}],
    "navigation": [{"label": "Dashboard", "route": "/dashboard", "icon": "home", "roles": ["admin"]}],
    "auth_config": {"roles": ["admin", "manager", "viewer"], "default_role": "viewer", "login_page": "/login"},
    "framework": "nextjs",
    "styling": "tailwind + shadcn/ui",
}

SAMPLE_CODE = {
    "file_tree": {
        "src/app/page.tsx": "'use client'\nexport default function Home() { return <div>Home</div> }",
        "src/app/dashboard/page.tsx": "'use client'\nexport default function Dashboard() { return <div>Dashboard</div> }",
        "src/app/layout.tsx": "export default function Layout({children}) { return <html><body>{children}</body></html> }",
        "package.json": '{"dependencies": {"react": "18", "next": "14"}}',
    },
    "package_json": '{"dependencies": {"react": "18", "next": "14"}}',
    "readme": "# Prototype\nnpm install && npm run dev",
    "total_files": 4,
    "framework": "nextjs",
}


# ─── DesignInterpreterSkill tests ───


@pytest.mark.asyncio
async def test_design_interpreter_produces_spec() -> None:
    llm = _mock_llm(json.dumps(SAMPLE_SPEC))
    skill = DesignInterpreterSkill(llm=llm)
    result = await skill.run(DesignInterpreterInput(
        design_artifacts=[{"name": "Architecture", "content": "modular_monolith"}],
    ))
    assert isinstance(result, PrototypeSpec)
    assert len(result.pages) >= 1
    assert result.framework == "nextjs"


# ─── PrototypeValidatorSkill tests ───


@pytest.mark.asyncio
async def test_validator_passes_valid_code() -> None:
    skill = PrototypeValidatorSkill()
    code = PrototypeCode(**SAMPLE_CODE)
    result = await skill.run(PrototypeValidatorInput(prototype_code=code))
    assert isinstance(result, ValidationResult)
    assert result.passed is True
    assert result.has_package_json is True
    assert result.has_layout is True
    assert result.has_pages is True
    assert result.file_count == 4


@pytest.mark.asyncio
async def test_validator_fails_empty_tree() -> None:
    skill = PrototypeValidatorSkill()
    code = PrototypeCode(file_tree={}, package_json="", readme="", total_files=0)
    result = await skill.run(PrototypeValidatorInput(prototype_code=code))
    assert result.passed is False
    assert any("empty" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_validator_warns_missing_routes() -> None:
    skill = PrototypeValidatorSkill()
    code = PrototypeCode(**SAMPLE_CODE)
    result = await skill.run(PrototypeValidatorInput(
        prototype_code=code,
        expected_routes=["/dashboard", "/products", "/settings"],
    ))
    assert any("settings" in w for w in result.warnings)


# ─── FeedbackAnalyzerSkill tests ───


@pytest.mark.asyncio
async def test_feedback_analyzer_specific_feedback() -> None:
    response = json.dumps({
        "changes": [
            {"component": "ProductTable", "change_type": "add", "description": "Add filter dropdown", "priority": "high"},
        ],
        "questions": [],
        "impact": ["ProductsPage"],
        "requires_design_change": False,
        "summary": "Add filter to product table",
    })
    llm = _mock_llm(response)
    skill = FeedbackAnalyzerSkill(llm=llm)
    result = await skill.run(FeedbackAnalysisInput(
        feedback_text="Add a filter dropdown on the product table",
        current_prototype_pages=["/dashboard", "/products"],
    ))
    assert isinstance(result, FeedbackAnalysis)
    assert len(result.changes) >= 1
    assert result.requires_design_change is False


@pytest.mark.asyncio
async def test_feedback_analyzer_vague_feedback() -> None:
    response = json.dumps({
        "changes": [],
        "questions": ["Which pages need improvement?", "What specifically looks wrong?"],
        "impact": [],
        "requires_design_change": False,
        "summary": "Vague feedback needs clarification",
    })
    llm = _mock_llm(response)
    skill = FeedbackAnalyzerSkill(llm=llm)
    result = await skill.run(FeedbackAnalysisInput(feedback_text="Make it better"))
    assert len(result.questions) >= 1
    assert len(result.changes) == 0


# ─── PreviewDeployment Provider tests ───


def test_all_providers_implement_interface() -> None:
    """All 4 providers implement the PreviewProvider base class."""
    for name, cls in PROVIDERS.items():
        provider = cls()
        assert isinstance(provider, PreviewProvider), f"{name} doesn't extend PreviewProvider"
        assert hasattr(provider, "deploy")
        assert hasattr(provider, "teardown")
        assert hasattr(provider, "get_status")


def test_get_provider_returns_correct_type() -> None:
    assert isinstance(get_provider("local_docker"), LocalDockerProvider)
    assert isinstance(get_provider("s3_static"), S3StaticProvider)
    assert isinstance(get_provider("vercel"), VercelProvider)
    assert isinstance(get_provider("netlify"), NetlifyProvider)


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown preview provider"):
        get_provider("unknown_provider")


# ─── Workflow tests ───


def test_prototype_workflow_compiles() -> None:
    workflow = PrototypeWorkflow()
    compiled = workflow.compile()
    assert compiled is not None


def test_build_prototype_graph_compiles() -> None:
    graph = build_prototype_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_create_initial_state_defaults() -> None:
    state = create_initial_state(project_id="00000000-0000-0000-0000-000000000001")
    assert state["project_id"] == "00000000-0000-0000-0000-000000000001"
    assert state["current_version"] == 1
    assert state["feedback_history"] == []
    assert state["preview_url"] == ""
    assert state["quality_score"] == 0.0


def test_quality_gate_pass() -> None:
    state = create_initial_state(project_id="test")
    state["quality_score"] = 85.0
    assert quality_gate(state) == "pass"


def test_quality_gate_retry() -> None:
    state = create_initial_state(project_id="test")
    state["quality_score"] = 50.0
    state["quality_retries"] = 0
    assert quality_gate(state) == "retry"


def test_quality_gate_max_retries() -> None:
    state = create_initial_state(project_id="test")
    state["quality_score"] = 50.0
    state["quality_retries"] = 2
    assert quality_gate(state) == "max_retries"


def test_workflow_metadata() -> None:
    w = PrototypeWorkflow()
    assert w.name == "prototype"
    assert "Next.js" in w.description or "prototype" in w.description.lower()


@pytest.mark.asyncio
async def test_full_workflow_passing() -> None:
    """Full pipeline: interpret → generate → deploy → quality(pass) → store."""
    llm = _mock_llm_sequence([
        json.dumps(SAMPLE_SPEC),           # interpret_design
        json.dumps(SAMPLE_CODE),           # generate_prototype (ui_generator)
        json.dumps({                        # quality_assessment
            "scores": {"page_coverage": 85, "component_coverage": 80, "mock_data_quality": 75,
                       "navigation_completeness": 90, "responsive_quality": 70, "role_differentiation": 70},
            "overall_score": 78.3, "passing": True, "gaps": [], "suggestions": [],
        }),
    ])

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    initial = create_initial_state(
        project_id="00000000-0000-0000-0000-000000000001",
        agent_run_id=str(uuid.uuid4()),
        llm=llm,
        session=session,
        design_artifacts=[{"name": "Architecture", "content": "{}"}],
        preview_provider="s3_static",  # Avoid Docker in tests
    )

    workflow = PrototypeWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    assert result.get("quality_score", 0) >= 70
    assert result.get("current_version") == 1


def _mock_llm_sequence(responses: list[str]) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=[AIMessage(content=r) for r in responses])
    return llm
