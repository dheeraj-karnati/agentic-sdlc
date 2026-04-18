"""Unit tests for BusinessContextRepository."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.context_store.models import AgentType, BusinessContext
from src.context_store.repository import BusinessContextRepository


@pytest.fixture
def project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    # session.add() is synchronous in real SQLAlchemy — use a plain MagicMock
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> BusinessContextRepository:
    return BusinessContextRepository(mock_session)


def _make_context(
    project_id: uuid.UUID,
    category: str = "requirements",
    title: str = "Test Title",
    content: str = "Test content",
    source_agent: AgentType | None = None,
    embedding: list[float] | None = None,
) -> BusinessContext:
    ctx = BusinessContext(
        id=uuid.uuid4(),
        project_id=project_id,
        category=category,
        title=title,
        content=content,
        source_agent=source_agent,
        embedding=embedding,
        metadata_={},
    )
    ctx.created_at = datetime.now(timezone.utc)
    return ctx


@pytest.mark.asyncio
async def test_store_context(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """store_context adds the entry, flushes, and refreshes."""
    await repo.store_context(
        project_id=project_id,
        category="requirements",
        title="Auth Requirements",
        content="Users must log in with SSO.",
        source_agent=AgentType.DISCOVER,
        metadata={"source": "interview"},
    )

    mock_session.add.assert_called_once()
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, BusinessContext)
    assert added_obj.project_id == project_id
    assert added_obj.category == "requirements"
    assert added_obj.title == "Auth Requirements"
    assert added_obj.content == "Users must log in with SSO."
    assert added_obj.source_agent == AgentType.DISCOVER
    assert added_obj.metadata_ == {"source": "interview"}

    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(added_obj)


@pytest.mark.asyncio
async def test_store_context_defaults(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """store_context uses sensible defaults for optional fields."""
    await repo.store_context(
        project_id=project_id,
        category="architecture",
        title=None,
        content="Microservices approach.",
    )

    added_obj = mock_session.add.call_args[0][0]
    assert added_obj.embedding is None
    assert added_obj.source_agent is None
    assert added_obj.metadata_ == {}


@pytest.mark.asyncio
async def test_search_similar(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """search_similar executes a query and returns results."""
    ctx1 = _make_context(project_id, embedding=[0.1] * 1536)
    ctx2 = _make_context(project_id, embedding=[0.2] * 1536)

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [ctx1, ctx2]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = result_mock

    results = await repo.search_similar(
        project_id=project_id,
        query_embedding=[0.15] * 1536,
        limit=5,
    )

    assert len(results) == 2
    assert results[0] is ctx1
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_similar_custom_limit(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """search_similar respects the limit parameter."""
    ctx1 = _make_context(project_id, embedding=[0.1] * 1536)

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [ctx1]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = result_mock

    results = await repo.search_similar(
        project_id=project_id,
        query_embedding=[0.1] * 1536,
        limit=1,
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_by_category(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """get_by_category returns entries matching the category."""
    ctx1 = _make_context(project_id, category="requirements")
    ctx2 = _make_context(project_id, category="requirements")

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [ctx1, ctx2]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = result_mock

    results = await repo.get_by_category(project_id, "requirements")

    assert len(results) == 2
    assert all(r.category == "requirements" for r in results)
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_category_empty(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """get_by_category returns empty list when no matches."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = result_mock

    results = await repo.get_by_category(project_id, "nonexistent")

    assert results == []


@pytest.mark.asyncio
async def test_get_all_for_project(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """get_all_for_project returns all entries for the project."""
    ctx1 = _make_context(project_id, category="requirements")
    ctx2 = _make_context(project_id, category="architecture")

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [ctx1, ctx2]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = result_mock

    results = await repo.get_all_for_project(project_id)

    assert len(results) == 2
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_for_project_empty(
    repo: BusinessContextRepository,
    mock_session: AsyncMock,
    project_id: uuid.UUID,
) -> None:
    """get_all_for_project returns empty list for project with no context."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = result_mock

    results = await repo.get_all_for_project(project_id)

    assert results == []