import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

@pytest.mark.asyncio
async def test_404_error(client):
    """Test 404 error handling."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_method_not_allowed(client):
    """Test method not allowed error."""
    response = await client.put("/health")
    assert response.status_code == 405