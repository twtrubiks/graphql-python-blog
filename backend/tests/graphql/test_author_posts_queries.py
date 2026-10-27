"""myPosts / postsByAuthor query 測試"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.post import PostStatus
from tests.factories import PostFactory


CONNECTION_FIELDS = """
    edges { node { title status } }
    pageInfo { totalCount currentPage totalPages hasNextPage hasPreviousPage }
"""

MY_POSTS_QUERY = f"""
query MyPosts($status: PostStatus, $page: Int, $limit: Int) {{
    myPosts(status: $status, page: $page, limit: $limit) {{ {CONNECTION_FIELDS} }}
}}
"""

POSTS_BY_AUTHOR_QUERY = f"""
query PostsByAuthor($authorId: Int, $authorUsername: String, $page: Int, $limit: Int) {{
    postsByAuthor(authorId: $authorId, authorUsername: $authorUsername, page: $page, limit: $limit) {{
        {CONNECTION_FIELDS}
    }}
}}
"""


@pytest_asyncio.fixture
async def author_posts(test_session, test_user, user_factory):
    """
    test_user 的文章（由新到舊）：
      Newest Draft（草稿）、Published（已發布）、Oldest Published（已發布）、
      Deleted（已發布但軟刪除，任何列表都不該出現）
    另有其他作者的一篇已發布文章。
    """
    now = datetime.now(timezone.utc)
    other = await user_factory.create(username="otherauthor")

    async def make(title, author_id, status, minutes_ago, deleted=False):
        post = await PostFactory.create(
            test_session,
            author_id=author_id,
            title=title,
            status=status,
            created_at=now - timedelta(minutes=minutes_ago),
        )
        if deleted:
            post.deleted_at = now

    await make("Newest Draft", test_user.id, PostStatus.DRAFT, 1)
    await make("Published", test_user.id, PostStatus.PUBLISHED, 2)
    await make("Oldest Published", test_user.id, PostStatus.PUBLISHED, 3)
    await make("Deleted", test_user.id, PostStatus.PUBLISHED, 0, deleted=True)
    await make("Other Author Post", other.id, PostStatus.PUBLISHED, 0)
    await test_session.commit()
    return other


async def run(client: AsyncClient, query: str, field: str, **variables) -> dict:
    response = await client.post("/graphql", json={"query": query, "variables": variables})
    assert response.status_code == 200
    data = response.json()
    assert "errors" not in data, data["errors"]
    return data["data"][field]


def titles(connection: dict) -> list[str]:
    return [edge["node"]["title"] for edge in connection["edges"]]


@pytest.mark.asyncio
class TestMyPosts:
    async def test_returns_own_posts_including_drafts(self, authenticated_client: AsyncClient, author_posts):
        """包含草稿、排除已刪除與他人的文章，依建立時間由新到舊"""
        result = await run(authenticated_client, MY_POSTS_QUERY, "myPosts")

        assert titles(result) == ["Newest Draft", "Published", "Oldest Published"]
        assert result["pageInfo"]["totalCount"] == 3

    async def test_filter_by_draft(self, authenticated_client: AsyncClient, author_posts):
        result = await run(authenticated_client, MY_POSTS_QUERY, "myPosts", status="DRAFT")

        assert titles(result) == ["Newest Draft"]
        assert result["edges"][0]["node"]["status"] == "DRAFT"
        assert result["pageInfo"]["totalCount"] == 1

    async def test_filter_by_published(self, authenticated_client: AsyncClient, author_posts):
        result = await run(authenticated_client, MY_POSTS_QUERY, "myPosts", status="PUBLISHED")

        assert titles(result) == ["Published", "Oldest Published"]
        assert result["pageInfo"]["totalCount"] == 2

    async def test_pagination(self, authenticated_client: AsyncClient, author_posts):
        result = await run(authenticated_client, MY_POSTS_QUERY, "myPosts", page=2, limit=2)

        assert titles(result) == ["Oldest Published"]
        assert result["pageInfo"] == {
            "totalCount": 3,
            "currentPage": 2,
            "totalPages": 2,
            "hasNextPage": False,
            "hasPreviousPage": True,
        }

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.post("/graphql", json={"query": MY_POSTS_QUERY})
        data = response.json()

        assert data["data"] is None
        assert data["errors"][0]["message"] == "Authentication required"


@pytest.mark.asyncio
class TestPostsByAuthor:
    async def test_by_author_id_only_published(self, client: AsyncClient, test_user, author_posts):
        """公開查詢只回傳已發布、未刪除的文章，不需要登入"""
        result = await run(client, POSTS_BY_AUTHOR_QUERY, "postsByAuthor", authorId=test_user.id)

        assert titles(result) == ["Published", "Oldest Published"]
        assert result["pageInfo"]["totalCount"] == 2

    async def test_by_author_username(self, client: AsyncClient, author_posts):
        result = await run(client, POSTS_BY_AUTHOR_QUERY, "postsByAuthor", authorUsername="testuser")

        assert titles(result) == ["Published", "Oldest Published"]

    async def test_author_id_takes_precedence_over_username(self, client: AsyncClient, author_posts):
        other = author_posts
        result = await run(
            client, POSTS_BY_AUTHOR_QUERY, "postsByAuthor",
            authorId=other.id, authorUsername="testuser",
        )

        assert titles(result) == ["Other Author Post"]

    async def test_unknown_username_returns_empty(self, client: AsyncClient, author_posts):
        result = await run(client, POSTS_BY_AUTHOR_QUERY, "postsByAuthor", authorUsername="nobody")

        assert result == {
            "edges": [],
            "pageInfo": {
                "totalCount": 0,
                "currentPage": 1,
                "totalPages": 0,
                "hasNextPage": False,
                "hasPreviousPage": False,
            },
        }

    async def test_pagination(self, client: AsyncClient, test_user, author_posts):
        result = await run(
            client, POSTS_BY_AUTHOR_QUERY, "postsByAuthor",
            authorId=test_user.id, page=1, limit=1,
        )

        assert titles(result) == ["Published"]
        assert result["pageInfo"]["hasNextPage"] is True
        assert result["pageInfo"]["hasPreviousPage"] is False

    async def test_requires_author(self, client: AsyncClient):
        response = await client.post("/graphql", json={"query": POSTS_BY_AUTHOR_QUERY})
        data = response.json()

        assert data["data"] is None
        assert data["errors"][0]["message"] == "Either author_id or author_username must be provided"
