"""Digitize Agent tasks — file ingestion, classification, and quality assessment."""

from src.agents.ingest.tasks.classify_and_structure_task import ClassifyAndStructureTask
from src.agents.ingest.tasks.generate_source_inventory_task import GenerateSourceInventoryTask
from src.agents.ingest.tasks.ingest_files_task import IngestFilesTask
from src.agents.ingest.tasks.quality_and_completeness_task import QualityAndCompletenessTask

__all__ = [
    "ClassifyAndStructureTask",
    "GenerateSourceInventoryTask",
    "IngestFilesTask",
    "QualityAndCompletenessTask",
]
