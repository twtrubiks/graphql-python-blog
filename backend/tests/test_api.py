import pytest

import app.main as app_main
from app.core.config import settings

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
    assert response.json() == {
        "message": "GraphQL Blog API",
        "graphql_endpoint": "/graphql",
        "graphql_playground": "/graphql" if settings.DEBUG else None,
    }

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


@pytest.mark.asyncio
async def test_cors_preflight_allows_frontend_with_credentials(client):
    """前端的 fetch 帶 credentials: 'include'，回應必須允許該來源並帶 Allow-Credentials，瀏覽器才會放行"""
    origin = settings.CORS_ORIGINS[0]
    response = await client.options("/graphql", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type",
    })

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_rejects_unknown_origin(client):
    response = await client.options("/graphql", headers={
        "Origin": "https://evil.example.com",
        "Access-Control-Request-Method": "POST",
    })

    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("debug, expected", [
    (True, ["init_db", "close_db"]),  # 開發模式啟動時自動建表
    (False, ["close_db"]),            # 正式環境的資料表由 alembic migration 建立
])
async def test_lifespan(monkeypatch, debug, expected):
    calls = []

    async def init_db():
        calls.append("init_db")

    async def close_db():
        calls.append("close_db")

    monkeypatch.setattr(app_main, "init_db", init_db)
    monkeypatch.setattr(app_main, "close_db", close_db)
    monkeypatch.setattr(settings, "DEBUG", debug)

    async with app_main.lifespan(app_main.app):
        assert calls == expected[:-1]  # 啟動完成、還沒關閉

    assert calls == expected

