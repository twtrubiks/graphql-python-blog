"""GraphQLContext.get() 只在屬性不存在時回傳預設值，不能吞掉 property 內部的錯誤"""
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.main
from app.main import GraphQLContext
from app.models.post import Post, PostStatus


def break_dataloaders(monkeypatch):
    """模擬建立 DataLoader 時的程式錯誤"""
    def broken(*args, **kwargs):
        raise AttributeError("broken dataloaders")

    monkeypatch.setattr(app.main, "DataLoaderContext", broken)


def test_get_returns_default_for_missing_key():
    context = GraphQLContext(db_session=None, session_factory=None)

    assert context.get("missing") is None
    assert context.get("missing", "fallback") == "fallback"


def test_get_returns_attributes_and_properties():
    session = object()
    context = GraphQLContext(db_session=session, session_factory=None)

    assert context.get("db_session") is session
    assert context["db_session"] is session
    assert context.get("user_id", "fallback") is None  # 沒有 request，未登入


def test_get_does_not_swallow_error_inside_property(monkeypatch):
    break_dataloaders(monkeypatch)
    context = GraphQLContext(db_session=None, session_factory=None)

    with pytest.raises(AttributeError, match="broken dataloaders"):
        context.get("dataloaders")


@pytest.mark.asyncio
async def test_broken_dataloaders_surface_as_error(
    client: AsyncClient, test_session: AsyncSession, test_user, monkeypatch
):
    """建立 DataLoader 出錯時要回報錯誤，而不是悄悄改走逐筆查詢、照常回傳資料"""
    test_session.add(Post(title="Post", slug="post", content="content",
                          status=PostStatus.PUBLISHED, author_id=test_user.id))
    await test_session.commit()
    break_dataloaders(monkeypatch)

    response = await client.post("/graphql", json={"query": "{ posts { edges { node { title likesCount } } } }"})

    data = response.json()
    assert "errors" in data
    assert data["data"] is None


@pytest.mark.asyncio
async def test_query_with_several_root_fields(client: AsyncClient, test_user, user_factory):
    """同一個查詢的根欄位會同時執行、共用請求的 session，不能因為同時建立連線而失敗"""
    other = await user_factory.create()
    query = "query($a: Int!, $b: Int!) { a: user(id: $a) { username } b: user(id: $b) { username } }"

    response = await client.post("/graphql", json={"query": query, "variables": {"a": test_user.id, "b": other.id}})

    assert response.json() == {"data": {"a": {"username": "testuser"}, "b": {"username": other.username}}}


def test_user_id_is_decoded_once(monkeypatch):
    """同一個請求的許多欄位都會讀 user_id，JWT 只解碼一次"""
    decoded = []

    def decode(token):
        decoded.append(token)
        return {"sub": "7"}

    monkeypatch.setattr(app.main, "decode_access_token", decode)
    context = GraphQLContext(db_session=None, session_factory=None)
    context.request = SimpleNamespace(headers={"Authorization": "Bearer abc"})

    assert (context.user_id, context.user_id) == (7, 7)
    assert decoded == ["abc"]

