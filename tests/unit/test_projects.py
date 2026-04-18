"""Unit tests for project API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_check():
    """Health endpoint returns ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


# NOTE: Tests that hit the database require a running PostgreSQL instance.
# For CI, use testcontainers or a test database with transaction rollback.
# Example:
#
# @pytest.mark.asyncio
# async def test_create_project():
#     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
#         response = await client.post("/api/projects/", json={
#             "name": "Test Project",
#             "description": "Testing project creation"
#         })
#     assert response.status_code == 201
#     data = response.json()
#     assert data["name"] == "Test Project"
#     assert data["status"] == "created"
