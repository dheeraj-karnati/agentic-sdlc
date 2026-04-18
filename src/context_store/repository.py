"""Repository class for business_context table operations."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.context_store.models import AgentType, BusinessContext

logger = logging.getLogger(__name__)

# The DB column is vector(1536). Embeddings with different dimensions are skipped.
DB_VECTOR_DIMENSION = 1536


class BusinessContextRepository:
    """Wraps all database operations for the business_context table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store_context(
        self,
        project_id: uuid.UUID,
        category: str,
        title: str | None,
        content: str,
        embedding: list[float] | None = None,
        source_agent: AgentType | None = None,
        metadata: dict | None = None,
    ) -> BusinessContext:
        """Store a new business context entry.

        If the embedding dimension doesn't match the DB column (1536),
        it is dropped with a warning rather than failing the insert.
        """
        # Validate embedding dimensions match the DB column
        if embedding is not None and len(embedding) != DB_VECTOR_DIMENSION:
            logger.warning(
                "Embedding dimension mismatch: got %d, DB expects %d — storing without embedding",
                len(embedding),
                DB_VECTOR_DIMENSION,
            )
            embedding = None

        entry = BusinessContext(
            project_id=project_id,
            category=category,
            title=title,
            content=content,
            embedding=embedding,
            source_agent=source_agent,
            metadata_=metadata or {},
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def search_similar(
        self,
        project_id: uuid.UUID,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[BusinessContext]:
        """Find similar context entries using pgvector cosine similarity."""
        stmt = (
            select(BusinessContext)
            .where(
                BusinessContext.project_id == project_id,
                BusinessContext.embedding.is_not(None),
            )
            .order_by(BusinessContext.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(
        self,
        project_id: uuid.UUID,
        category: str,
    ) -> list[BusinessContext]:
        """Get all context entries for a project filtered by category."""
        stmt = (
            select(BusinessContext)
            .where(
                BusinessContext.project_id == project_id,
                BusinessContext.category == category,
            )
            .order_by(BusinessContext.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_for_project(
        self,
        project_id: uuid.UUID,
    ) -> list[BusinessContext]:
        """Get all context entries for a project."""
        stmt = (
            select(BusinessContext)
            .where(BusinessContext.project_id == project_id)
            .order_by(BusinessContext.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())