"""Unit tests for the Discovery Agent workflow (new architecture)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.discover.agent import (
    DiscoverWorkflow,
    build_discover_graph,
    clarification_check,
    create_initial_state,
    quality_gate,
)


# ─── Sample LLM Responses ───

CLASSIFY_RESPONSE = json.dumps({
    "items": [
        {
            "source": "raw_input",
            "content_type": "brd",
            "language": "",
            "content": "Orders over $10,000 require manager approval.",
        }
    ],
    "classification_reasoning": "Formal requirements language.",
})

RULE_EXTRACTION_RESPONSE = json.dumps({
    "rules": [
        {
            "rule_id": "BR-001",
            "rule_name": "Large order approval",
            "description": "Orders over $10,000 require manager approval",
            "trigger_condition": "Order total exceeds $10,000",
            "action": "Route to manager for approval",
            "exceptions": ["VIP customers are auto-approved"],
            "source_reference": "BRD section 3.1",
            "confidence": "high",
            "related_entities": ["Order", "Manager"],
            "validation_logic": "Check order.total > 10000",
        }
    ]
})

ENTITY_EXTRACTION_RESPONSE = json.dumps({
    "entities": [
        {
            "entity_name": "Order",
            "entity_type": "data_object",
            "description": "A purchase order",
            "attributes": [{"name": "total", "type": "decimal", "constraints": "NOT NULL"}],
            "relationships": [{"related_entity": "Customer", "relationship_type": "belongs_to", "cardinality": "N:1"}],
            "business_rules_involved": ["BR-001"],
        }
    ]
})

CONFLICT_RESPONSE = json.dumps({
    "contradictions": [],
    "gaps": [],
    "ambiguities": [],
    "redundancies": [],
    "total_conflicts": 0,
})

DOC_EXTRACTION_RESPONSE = json.dumps({
    "document_type": "brd",
    "stakeholders": ["Product Owner"],
    "objectives": ["Modernize order system"],
    "scope": "Full order management lifecycle",
    "constraints": [],
    "assumptions": [],
    "functional_requirements": [
        {"id": "FR-1", "description": "Manager approval for large orders", "priority": "high", "source_section": "3.1", "type": "functional"}
    ],
    "non_functional_requirements": [],
    "acceptance_criteria": [],
    "out_of_scope": [],
    "decisions_made": [],
    "action_items": [],
    "open_questions": [],
    "attendees": [],
    "features_described": [],
    "user_workflows": [],
    "business_rules": [],
    "raw_extracted_text": "",
})

UNDERSTANDING_RESPONSE = json.dumps({
    "system_purpose": "A" * 200,
    "domain_model": "B" * 200,
    "business_rules_catalog": [{"domain_area": "Orders", "rules": [{"rule_name": "approval"}]}],
    "technology_assessment": "Legacy system assessment",
    "user_workflows": [{"journey_name": "Order", "actor": "Buyer", "steps": ["Create order"]}],
    "data_flow_description": "Orders flow from UI to backend",
    "integration_points": [],
    "modernization_recommendations": [],
})

QUESTIONS_RESPONSE = json.dumps({"questions": []})

QUALITY_PASS_RESPONSE = json.dumps({
    "scores": {"completeness": 85, "depth": 80, "consistency": 90, "traceability": 75, "actionability": 80},
    "overall_score": 82.25,
    "suggestions": [],
    "passing": True,
})

QUALITY_FAIL_RESPONSE = json.dumps({
    "scores": {"completeness": 30, "depth": 20, "consistency": 50, "traceability": 30, "actionability": 25},
    "overall_score": 30.0,
    "suggestions": ["Needs more business rules", "No entity relationships found"],
    "passing": False,
})

QUESTIONS_WITH_ITEMS_RESPONSE = json.dumps({
    "questions": [
        {
            "question": "What is the max order amount for auto-approval?",
            "why_asking": "Not specified in the BRD",
            "impact_if_unanswered": "Cannot set approval threshold",
            "suggested_options": ["$5,000", "$10,000", "$25,000"],
            "related_findings": ["BR-001"],
            "priority": "blocking",
        }
    ]
})


def _mock_llm_sequence(responses: list[str]) -> MagicMock:
    """Create a mock LLM that returns responses in sequence."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        side_effect=[AIMessage(content=r) for r in responses]
    )
    return llm


# ─── quality_gate routing tests ───


def test_quality_gate_pass() -> None:
    state = create_initial_state(project_id="test-id", document_text="")
    state["quality_score"] = 85.0
    state["quality_retries"] = 0
    assert quality_gate(state) == "pass"


def test_quality_gate_retry() -> None:
    state = create_initial_state(project_id="test-id", document_text="")
    state["quality_score"] = 50.0
    state["quality_retries"] = 0
    assert quality_gate(state) == "retry"


def test_quality_gate_max_retries() -> None:
    state = create_initial_state(project_id="test-id", document_text="")
    state["quality_score"] = 50.0
    state["quality_retries"] = 2
    assert quality_gate(state) == "max_retries_reached"


# ─── clarification_check routing tests ───


def test_clarification_check_has_questions() -> None:
    state = create_initial_state(project_id="test-id", document_text="")
    state["pending_questions"] = [{"question": "test?"}]
    assert clarification_check(state) == "has_questions"


def test_clarification_check_clear() -> None:
    state = create_initial_state(project_id="test-id", document_text="")
    state["pending_questions"] = []
    assert clarification_check(state) == "clear"


def test_clarification_check_skip_clarity() -> None:
    state = create_initial_state(project_id="test-id", document_text="")
    state["skip_clarity"] = True
    state["pending_questions"] = [{"question": "test?"}]
    assert clarification_check(state) == "clear"


# ─── DiscoverWorkflow tests ───


def test_workflow_builds_graph() -> None:
    """DiscoverWorkflow.build_graph() returns a valid StateGraph."""
    workflow = DiscoverWorkflow()
    graph = workflow.build_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_backward_compat_build_discover_graph() -> None:
    """build_discover_graph() still works for backward compatibility."""
    graph = build_discover_graph()
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.asyncio
async def test_full_workflow_clear_path() -> None:
    """Full workflow: classify → analyze → understand → questions → quality(pass) → store."""
    # The workflow makes many LLM calls across multiple tasks.
    # Order: classify, doc_extraction, rules, entities, conflict, understanding, questions, quality
    llm = _mock_llm_sequence([
        CLASSIFY_RESPONSE,          # parse_and_classify
        DOC_EXTRACTION_RESPONSE,    # deep_analysis: doc_extraction skill
        RULE_EXTRACTION_RESPONSE,   # deep_analysis: business_rule_extraction skill
        ENTITY_EXTRACTION_RESPONSE, # deep_analysis: entity_extraction skill
        CONFLICT_RESPONSE,          # deep_analysis: conflict_detection skill
        UNDERSTANDING_RESPONSE,     # generate_understanding
        QUESTIONS_RESPONSE,         # generate_questions
        QUALITY_PASS_RESPONSE,      # quality_assessment
    ])

    mock_repo = MagicMock()
    mock_repo.store_context = AsyncMock()
    mock_embed = AsyncMock(return_value=[0.1] * 1536)

    initial = create_initial_state(
        project_id="00000000-0000-0000-0000-000000000001",
        document_text="Orders over $10,000 require manager approval.",
        llm=llm,
        repository=mock_repo,
        embed_fn=mock_embed,
    )

    workflow = DiscoverWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    # Quality passed
    assert result.get("quality_score", 0) >= 70
    # Items were stored (rules + entities + understanding)
    assert result.get("stored_count", 0) >= 1
    # No pending questions
    assert result.get("pending_questions", []) == []


@pytest.mark.asyncio
async def test_full_workflow_with_questions() -> None:
    """Full workflow stops with pending questions for human review."""
    llm = _mock_llm_sequence([
        CLASSIFY_RESPONSE,
        DOC_EXTRACTION_RESPONSE,
        RULE_EXTRACTION_RESPONSE,
        ENTITY_EXTRACTION_RESPONSE,
        CONFLICT_RESPONSE,
        UNDERSTANDING_RESPONSE,
        QUESTIONS_WITH_ITEMS_RESPONSE,  # Questions found
        QUALITY_PASS_RESPONSE,
    ])

    mock_repo = MagicMock()
    mock_repo.store_context = AsyncMock()
    mock_embed = AsyncMock(return_value=[0.1] * 1536)

    initial = create_initial_state(
        project_id="00000000-0000-0000-0000-000000000001",
        document_text="Orders over $10,000 require manager approval.",
        llm=llm,
        repository=mock_repo,
        embed_fn=mock_embed,
    )

    workflow = DiscoverWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    # Should have pending questions
    assert len(result.get("pending_questions", [])) == 1
    assert result["pending_questions"][0]["priority"] == "blocking"


@pytest.mark.asyncio
async def test_workflow_quality_retry_loop() -> None:
    """Workflow retries deep analysis when quality is below threshold."""
    # First pass fails quality, second pass succeeds
    llm = _mock_llm_sequence([
        # First pass
        CLASSIFY_RESPONSE,
        DOC_EXTRACTION_RESPONSE,
        RULE_EXTRACTION_RESPONSE,
        ENTITY_EXTRACTION_RESPONSE,
        CONFLICT_RESPONSE,
        UNDERSTANDING_RESPONSE,
        QUESTIONS_RESPONSE,
        QUALITY_FAIL_RESPONSE,      # Fail → retry
        # Retry (starts from deep_analysis)
        DOC_EXTRACTION_RESPONSE,
        RULE_EXTRACTION_RESPONSE,
        ENTITY_EXTRACTION_RESPONSE,
        CONFLICT_RESPONSE,
        UNDERSTANDING_RESPONSE,
        QUESTIONS_RESPONSE,
        QUALITY_PASS_RESPONSE,      # Pass → store
    ])

    mock_repo = MagicMock()
    mock_repo.store_context = AsyncMock()
    mock_embed = AsyncMock(return_value=[0.1] * 1536)

    initial = create_initial_state(
        project_id="00000000-0000-0000-0000-000000000001",
        document_text="Orders over $10,000 require manager approval.",
        llm=llm,
        repository=mock_repo,
        embed_fn=mock_embed,
    )

    workflow = DiscoverWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    # Quality retries should have been incremented
    assert result.get("quality_retries", 0) >= 1
    # Should eventually pass
    assert result.get("quality_score", 0) >= 70
