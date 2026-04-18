"""Unit tests for Discovery Agent tasks (mock LLM calls)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.discover.tasks.generate_clarification_questions_task import (
    ClarificationQuestionsInput,
    ClarificationQuestionsOutput,
    GenerateClarificationQuestionsTask,
)
from src.agents.discover.tasks.generate_system_understanding_task import (
    GenerateSystemUnderstandingTask,
    SystemUnderstanding,
    SystemUnderstandingInput,
)
from src.agents.discover.tasks.parse_and_classify_task import (
    ClassifiedInputs,
    InputFile,
    ParseAndClassifyInput,
    ParseAndClassifyTask,
)
from src.agents.discover.tasks.quality_assessment_task import (
    QualityAssessment,
    QualityAssessmentInput,
    QualityAssessmentTask,
    QualityScores,
)


def _mock_llm(content: str) -> MagicMock:
    """Create a mock LLM that returns given content."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return llm


# ─── ParseAndClassifyTask tests ───


@pytest.mark.asyncio
async def test_parse_and_classify_classifies_code() -> None:
    """ParseAndClassifyTask correctly classifies source code."""
    response = json.dumps({
        "items": [
            {
                "source": "app.py",
                "content_type": "source_code",
                "language": "python",
                "content": "from flask import Flask",
            }
        ],
        "classification_reasoning": "Contains Python imports",
    })
    llm = _mock_llm(response)
    task = ParseAndClassifyTask()

    result = await task.execute(
        ParseAndClassifyInput(
            files=[InputFile(filename="app.py", content="from flask import Flask")],
        ),
        llm=llm,
    )

    assert isinstance(result, ClassifiedInputs)
    assert len(result.items) == 1
    assert result.items[0].content_type == "source_code"
    assert result.items[0].language == "python"


@pytest.mark.asyncio
async def test_parse_and_classify_classifies_raw_text() -> None:
    """ParseAndClassifyTask handles raw text input."""
    response = json.dumps({
        "items": [
            {
                "source": "raw_input",
                "content_type": "brd",
                "language": "",
                "content": "The system shall provide user authentication...",
            }
        ],
        "classification_reasoning": "Formal requirements language",
    })
    llm = _mock_llm(response)
    task = ParseAndClassifyTask()

    result = await task.execute(
        ParseAndClassifyInput(raw_text="The system shall provide user authentication..."),
        llm=llm,
    )

    assert result.items[0].content_type == "brd"


@pytest.mark.asyncio
async def test_parse_and_classify_validates_output() -> None:
    """ParseAndClassifyTask fails validation on empty items."""
    task = ParseAndClassifyTask()
    output = ClassifiedInputs(items=[], classification_reasoning="nothing")
    assert task.validate(output) is False


@pytest.mark.asyncio
async def test_parse_and_classify_validates_missing_type() -> None:
    """ParseAndClassifyTask fails validation when content_type is empty."""
    task = ParseAndClassifyTask()
    from src.agents.discover.tasks.parse_and_classify_task import ClassifiedItem

    output = ClassifiedInputs(
        items=[ClassifiedItem(source="x", content_type="", content="text")],
    )
    assert task.validate(output) is False


# ─── GenerateSystemUnderstandingTask tests ───


@pytest.mark.asyncio
async def test_generate_understanding_produces_output() -> None:
    """GenerateSystemUnderstandingTask generates a SystemUnderstanding."""
    response = json.dumps({
        "system_purpose": "A" * 200,
        "domain_model": "B" * 200,
        "business_rules_catalog": [{"domain_area": "Auth", "rules": []}],
        "technology_assessment": "Java 8 with Spring Boot",
        "user_workflows": [
            {"journey_name": "Login", "actor": "User", "steps": ["1. Enter credentials"]}
        ],
        "data_flow_description": "Data flows from UI to API to DB",
        "integration_points": [],
        "modernization_recommendations": [],
    })
    llm = _mock_llm(response)
    task = GenerateSystemUnderstandingTask()

    result = await task.execute(
        SystemUnderstandingInput(deep_analysis={"business_rules": []}),
        llm=llm,
    )

    assert isinstance(result, SystemUnderstanding)
    assert len(result.system_purpose) >= 100
    assert len(result.domain_model) >= 100


@pytest.mark.asyncio
async def test_generate_understanding_validation_requires_depth() -> None:
    """Validation fails when system_purpose is too short."""
    task = GenerateSystemUnderstandingTask()
    output = SystemUnderstanding(
        system_purpose="Short.",
        domain_model="Also short.",
    )
    assert task.validate(output) is False


# ─── GenerateClarificationQuestionsTask tests ───


@pytest.mark.asyncio
async def test_clarification_questions_generated() -> None:
    """GenerateClarificationQuestionsTask produces questions from conflicts."""
    response = json.dumps({
        "questions": [
            {
                "question": "What is the max login attempts?",
                "why_asking": "BRD and code disagree",
                "impact_if_unanswered": "Cannot finalize auth design",
                "suggested_options": ["3 attempts", "5 attempts"],
                "related_findings": ["BRD 3.2", "auth_service.py"],
                "priority": "blocking",
            }
        ]
    })
    llm = _mock_llm(response)
    task = GenerateClarificationQuestionsTask()

    result = await task.execute(
        ClarificationQuestionsInput(
            conflict_report={"contradictions": [{"description": "login attempts mismatch"}]},
        ),
        llm=llm,
    )

    assert isinstance(result, ClarificationQuestionsOutput)
    assert len(result.questions) == 1
    assert result.questions[0].priority == "blocking"


@pytest.mark.asyncio
async def test_clarification_validation_requires_content() -> None:
    """Validation fails when question text is empty."""
    task = GenerateClarificationQuestionsTask()
    from src.agents.discover.tasks.generate_clarification_questions_task import (
        ClarificationQuestion,
    )

    output = ClarificationQuestionsOutput(
        questions=[ClarificationQuestion(question="", why_asking="")]
    )
    assert task.validate(output) is False


# ─── QualityAssessmentTask tests ───


@pytest.mark.asyncio
async def test_quality_assessment_passing() -> None:
    """QualityAssessmentTask scores passing output correctly."""
    response = json.dumps({
        "scores": {
            "completeness": 85,
            "depth": 80,
            "consistency": 90,
            "traceability": 75,
            "actionability": 80,
        },
        "overall_score": 82.25,
        "suggestions": [],
        "passing": True,
    })
    llm = _mock_llm(response)
    task = QualityAssessmentTask()

    result = await task.execute(
        QualityAssessmentInput(
            deep_analysis={"business_rules": [{"rule_name": "test"}]},
            system_understanding={"system_purpose": "A detailed description..."},
            clarification_questions={"questions": []},
        ),
        llm=llm,
    )

    assert isinstance(result, QualityAssessment)
    assert result.overall_score >= 70
    assert result.passing is True


@pytest.mark.asyncio
async def test_quality_assessment_failing() -> None:
    """QualityAssessmentTask returns suggestions when below threshold."""
    response = json.dumps({
        "scores": {
            "completeness": 30,
            "depth": 20,
            "consistency": 50,
            "traceability": 30,
            "actionability": 25,
        },
        "overall_score": 30.0,
        "suggestions": [
            "Business rules need more detail",
            "No entities extracted",
        ],
        "passing": False,
    })
    llm = _mock_llm(response)
    task = QualityAssessmentTask()

    result = await task.execute(
        QualityAssessmentInput(
            deep_analysis={},
            system_understanding={},
            clarification_questions={},
        ),
        llm=llm,
    )

    assert result.overall_score < 70
    assert result.passing is False
    assert len(result.suggestions) == 2


@pytest.mark.asyncio
async def test_quality_validation_rejects_invalid_scores() -> None:
    """Validation fails when scores are out of range."""
    task = QualityAssessmentTask()

    out_of_range = QualityAssessment(
        scores=QualityScores(completeness=150),
        overall_score=80,
    )
    assert task.validate(out_of_range) is False

    negative = QualityAssessment(
        scores=QualityScores(depth=-10),
        overall_score=50,
    )
    assert task.validate(negative) is False
