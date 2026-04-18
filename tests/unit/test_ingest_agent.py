"""Unit tests for the Digitize Agent (D1)."""

import pytest

from src.agents.ingest.agent import (
    IngestWorkflow,
    build_ingest_graph,
    create_initial_state,
)
from src.agents.ingest.skills.code_parsing_skill import (
    CodebaseAnalysis,
    CodeParsingInput,
    CodeParsingSkill,
    SourceFile,
)
from src.agents.ingest.skills.text_chunking_skill import (
    TextChunkingInput,
    TextChunkingOutput,
    TextChunkingSkill,
)
from src.agents.ingest.tasks.generate_source_inventory_task import (
    GenerateSourceInventoryInput,
    GenerateSourceInventoryTask,
    SourceInventory,
)
from src.agents.ingest.tasks.quality_and_completeness_task import (
    DigitizeQualityReport,
    QualityAndCompletenessInput,
    QualityAndCompletenessTask,
)
from src.agents.ingest.tasks.classify_and_structure_task import StructuredInputBundle


# ─── Skill Tests ───


@pytest.mark.asyncio
async def test_code_parsing_extracts_structure() -> None:
    skill = CodeParsingSkill()
    result = await skill.run(CodeParsingInput(source_files=[
        SourceFile(file_path="app.py", content="from flask import Flask\napp = Flask(__name__)\n\n@app.get('/health')\ndef health(): return 'ok'", language="python"),
        SourceFile(file_path="models.py", content="class User:\n    pass\nclass Order:\n    pass", language="python"),
    ]))
    assert isinstance(result, CodebaseAnalysis)
    assert result.total_files == 2
    assert result.total_lines > 0
    assert "Flask" in result.technology_stack
    assert len(result.api_endpoints) >= 1


@pytest.mark.asyncio
async def test_text_chunking_paragraph_strategy() -> None:
    skill = TextChunkingSkill()
    long_text = "\n\n".join(f"Paragraph {i}. " + "word " * 100 for i in range(20))
    result = await skill.run(TextChunkingInput(
        long_text=long_text, chunk_strategy="paragraph", max_tokens_per_chunk=500,
    ))
    assert isinstance(result, TextChunkingOutput)
    assert result.chunk_count >= 2
    assert result.total_tokens > 0
    for chunk in result.chunks:
        assert chunk.chunk_id
        assert chunk.text


@pytest.mark.asyncio
async def test_text_chunking_short_text_single_chunk() -> None:
    skill = TextChunkingSkill()
    result = await skill.run(TextChunkingInput(long_text="Short text.", chunk_strategy="paragraph"))
    assert result.chunk_count == 1


# ─── Task Tests ───


@pytest.mark.asyncio
async def test_generate_inventory_counts_words() -> None:
    task = GenerateSourceInventoryTask()
    bundle = StructuredInputBundle(
        sources=[
            {"source_id": "s1", "original_filename": "spec.md", "content_type": "brd",
             "text": "word " * 1000, "key_topics": ["auth"], "confidence": 0.9, "chunks": [],
             "input_type": "document", "language": "en", "domain": "", "parsed_data": {}},
        ],
        is_legacy_modernization=False,
        has_source_code=False,
        has_requirements=True,
        total_sources=1,
    )
    result = await task.execute(GenerateSourceInventoryInput(
        structured_bundle=bundle,
    ))
    assert isinstance(result, SourceInventory)
    assert result.total_sources == 1
    assert result.total_words == 1000
    assert "brd" in result.content_type_distribution


@pytest.mark.asyncio
async def test_quality_report_passes_with_good_input() -> None:
    task = QualityAndCompletenessTask()
    inventory = SourceInventory(
        entries=[
            {"source_id": "s1", "original_filename": "spec.md", "content_type": "brd",
             "word_count": 5000, "key_topics": ["auth", "orders"], "quality_score": 0.8, "chunk_count": 3},
            {"source_id": "s2", "original_filename": "app.py", "content_type": "source_code",
             "word_count": 2000, "key_topics": ["flask"], "quality_score": 0.7, "chunk_count": 1},
        ],
        total_sources=2,
        total_words=7000,
        content_type_distribution={"brd": 1, "source_code": 1},
        is_legacy_modernization=True,
    )
    result = await task.execute(QualityAndCompletenessInput(source_inventory=inventory))
    assert isinstance(result, DigitizeQualityReport)
    assert result.passing is True
    assert result.overall_score > 50


@pytest.mark.asyncio
async def test_quality_report_warns_on_single_source() -> None:
    task = QualityAndCompletenessTask()
    inventory = SourceInventory(
        entries=[{"source_id": "s1", "original_filename": "x.txt", "content_type": "unknown",
                  "word_count": 100, "key_topics": [], "quality_score": 0.2, "chunk_count": 0}],
        total_sources=1,
        total_words=100,
        content_type_distribution={"unknown": 1},
        is_legacy_modernization=False,
    )
    result = await task.execute(QualityAndCompletenessInput(source_inventory=inventory))
    assert any("one source" in w.lower() for w in result.warnings)


# ─── Workflow Tests ───


def test_digitize_workflow_compiles() -> None:
    workflow = IngestWorkflow()
    compiled = workflow.compile()
    assert compiled is not None


def test_build_ingest_graph_compiles() -> None:
    graph = build_ingest_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_create_initial_state_defaults() -> None:
    state = create_initial_state(project_id="00000000-0000-0000-0000-000000000001")
    assert state["project_id"] == "00000000-0000-0000-0000-000000000001"
    assert state["files"] == []
    assert state["task_outputs"] == {}
    assert state["errors"] == []


def test_workflow_metadata() -> None:
    w = IngestWorkflow()
    assert w.name == "ingest"
    assert "ingest" in w.description.lower() or "parse" in w.description.lower()
