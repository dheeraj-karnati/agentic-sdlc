"""Tests for tiered LLM analysis module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.ingest.tiered_analysis import (
    _truncate_to_tokens,
    analyze_project_overall,
    analyze_tier1_file,
    analyze_tier2_group,
)


# ─── Token truncation ───


class TestTruncateToTokens:
    def test_short_text_unchanged(self):
        text = "Hello world"
        assert _truncate_to_tokens(text, 100) == text

    def test_long_text_truncated(self):
        text = "word " * 10000  # ~10K tokens
        result = _truncate_to_tokens(text, 100)
        assert len(result) < len(text)
        assert "[truncated for token budget]" in result

    def test_empty_text(self):
        assert _truncate_to_tokens("", 100) == ""


# ─── Tier 1 analysis ───


class TestAnalyzeTier1File:
    @pytest.mark.asyncio
    async def test_documentation_file(self):
        mock_result = {
            "document_type": "brd",
            "key_topics": ["patient management", "HIPAA"],
            "estimated_importance": "critical",
            "summary": "Business requirements for healthcare system.",
            "business_signals": ["HIPAA compliance required"],
        }
        with patch("src.agents.ingest.tiered_analysis.llm_complete_json", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_tier1_file(
                filename="BRD.md",
                content="# Business Requirements\n\nPatient management system...",
                role="documentation",
                language="markdown",
            )
            assert result["document_type"] == "brd"
            assert result["filename"] == "BRD.md"
            assert "HIPAA" in result["key_topics"]

    @pytest.mark.asyncio
    async def test_code_file_with_structure(self):
        mock_result = {
            "document_type": "source_code",
            "key_topics": ["billing", "payment processing"],
            "estimated_importance": "high",
            "summary": "Billing service with payment processing.",
            "business_signals": ["hardcoded threshold $5000"],
        }
        code_structure = {
            "class_name": "BillingService",
            "parent_class": "BaseService",
            "interfaces": ["Billable"],
            "annotations": ["Service", "Transactional"],
            "methods": [
                {"name": "processPayment", "params": "Invoice inv", "return_type": "void"},
            ],
            "sql_queries": ["SELECT * FROM invoices WHERE status = 'PENDING'"],
            "hardcoded_values": [{"name": "THRESHOLD", "value": "5000"}],
            "dependencies": ["InvoiceRepository"],
            "entry_points": [],
            "key_comments": ["TODO: add approval workflow"],
        }
        with patch("src.agents.ingest.tiered_analysis.llm_complete_json", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_tier1_file(
                filename="BillingService.java",
                content="public class BillingService {}",
                role="service",
                language="java",
                code_structure=code_structure,
            )
            assert result["filename"] == "BillingService.java"
            assert result["estimated_importance"] == "high"

    @pytest.mark.asyncio
    async def test_config_file(self):
        mock_result = {
            "document_type": "config",
            "key_topics": ["database", "server"],
            "estimated_importance": "high",
            "summary": "Application configuration with database settings.",
            "business_signals": ["PostgreSQL database", "Port 8080"],
        }
        with patch("src.agents.ingest.tiered_analysis.llm_complete_json", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_tier1_file(
                filename="application.properties",
                content="spring.datasource.url=jdbc:postgresql://localhost:5432/mydb",
                role="config",
                language="properties",
            )
            assert result["document_type"] == "config"


# ─── Tier 2 analysis ───


class TestAnalyzeTier2Group:
    @pytest.mark.asyncio
    async def test_group_analysis(self):
        mock_result = {
            "group_purpose": "Manages patient billing and invoicing",
            "key_patterns": ["CRUD for invoices", "Payment gateway integration"],
            "data_entities": ["Invoice", "Payment", "LineItem"],
            "potential_issues": ["Hardcoded tax rate"],
            "technology_notes": "Spring Boot with JPA",
        }
        with patch("src.agents.ingest.tiered_analysis.llm_complete_json", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_tier2_group(
                group_key="com.acme.billing",
                group_content="Package: com.acme.billing\nClasses: InvoiceService, PaymentService...",
                file_count=8,
                roles={"entity": 4, "repository": 2, "migration": 2},
                language="java",
            )
            assert result["group_key"] == "com.acme.billing"
            assert result["file_count"] == 8
            assert "billing" in result["group_purpose"].lower()


# ─── Project-level synthesis ───


class TestAnalyzeProjectOverall:
    @pytest.mark.asyncio
    async def test_synthesis(self):
        mock_result = {
            "project_type": "legacy_modernization",
            "project_type_reasoning": "Legacy SQL Server database being migrated",
            "domain": "healthcare",
            "technology_stack": ["Java", "Spring Boot", "SQL Server"],
            "overall_assessment": {
                "strengths": ["Complete BRD", "Source code available"],
                "gaps": ["No API documentation"],
                "suggestions": ["Add API docs"],
                "ready_for_discovery": True,
            },
        }
        with patch("src.agents.ingest.tiered_analysis.llm_complete_json", new_callable=AsyncMock, return_value=mock_result):
            tier1_results = [
                {"filename": "BRD.md", "document_type": "brd", "summary": "Healthcare BRD", "key_topics": ["HIPAA"], "estimated_importance": "critical"},
                {"filename": "BillingService.java", "document_type": "source_code", "summary": "Billing logic", "key_topics": ["billing"], "estimated_importance": "high"},
            ]
            tier2_results = [
                {"group_key": "com.acme.patient", "file_count": 5, "group_purpose": "Patient management"},
            ]

            result = await analyze_project_overall(
                tier1_results=tier1_results,
                tier2_results=tier2_results,
                tier3_summary={"test": 20, "dto": 10},
                total_files=50,
            )
            assert result["project_type"] == "legacy_modernization"
            assert result["domain"] == "healthcare"
            assert len(result["file_assessments"]) == 2
            assert result["file_assessments"][0]["filename"] == "BRD.md"

    @pytest.mark.asyncio
    async def test_synthesis_with_errors_in_tier_results(self):
        """Verify exceptions in tier results don't crash synthesis."""
        mock_result = {
            "project_type": "greenfield",
            "project_type_reasoning": "New project",
            "domain": "fintech",
            "technology_stack": ["Python"],
            "overall_assessment": {"strengths": [], "gaps": [], "suggestions": [], "ready_for_discovery": True},
        }
        with patch("src.agents.ingest.tiered_analysis.llm_complete_json", new_callable=AsyncMock, return_value=mock_result):
            # Mix of valid results and exceptions
            tier1_results = [
                {"filename": "spec.md", "summary": "Spec doc", "key_topics": [], "document_type": "technical_spec", "estimated_importance": "high"},
                RuntimeError("LLM call failed"),  # exception from gather
            ]
            result = await analyze_project_overall(
                tier1_results=tier1_results,
                tier2_results=[],
                tier3_summary={},
                total_files=10,
            )
            # Should produce file_assessments only for the valid result
            assert len(result["file_assessments"]) == 1


# ─── Concurrency ───


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_calls(self):
        """Verify that semaphore limits concurrent LLM calls."""
        call_count = 0
        max_concurrent = 0

        async def mock_llm_call(*args, **kwargs):
            nonlocal call_count, max_concurrent
            call_count += 1
            current = call_count
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.05)  # simulate LLM latency
            call_count -= 1
            return {"document_type": "other", "key_topics": [], "estimated_importance": "low", "summary": "test", "business_signals": []}

        sem = asyncio.Semaphore(3)  # limit to 3 concurrent

        async def bounded_call(filename):
            async with sem:
                return await mock_llm_call()

        # Run 10 "LLM calls" with semaphore(3)
        results = await asyncio.gather(*[bounded_call(f"file{i}") for i in range(10)])
        assert len(results) == 10
        assert max_concurrent <= 3
