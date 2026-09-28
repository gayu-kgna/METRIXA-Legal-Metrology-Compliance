import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint returns 200, healthy DB, and legal framework identifier."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["platform"] == "METRIXA"
    assert "Legal Metrology" in data["data"]["legal_framework"]
    assert data["data"]["database"] == "connected"

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns platform metadata and doc links."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "METRIXA"
    assert "/api/v1/docs" in data["docs_url"]

@pytest.mark.asyncio
async def test_top_level_health_endpoint(client: AsyncClient):
    """Test top-level /health endpoint returns HTTP 200 and healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["platform"] == "METRIXA"

