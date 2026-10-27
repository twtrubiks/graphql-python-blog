"""文章列表的第 2 頁：posts / postsByTag / postsByTags 共用相同的分頁計算"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus
from app.models.tag import Tag
from app.models.user import User


PAGE_FIELDS = """
    edges { node { title } }
    pageInfo { hasNextPage hasPreviousPage totalCount currentPage totalPages }
"""


@pytest.fixture
async def tagged_posts(test_session: AsyncSession, test_user: User):
    """Post 1（最新）到 Post 5 同時有 python 與 web；草稿與已刪除的文章最新，但不能出現在列表或計數中"""
    python_tag = Tag(name="python", slug="python")
    web_tag = Tag(name="web", slug="web")
    now = datetime.now(timezone.utc)

    def post(title, minutes_ago, tags, **kwargs):
        return Post(
            title=title,
            slug=title.lower().replace(" ", "-"),
            content=title,
            status=kwargs.pop("status", PostStatus.PUBLISHED),
            author_id=test_user.id,
            created_at=now - timedelta(minutes=minutes_ago),
            tags=tags,
            **kwargs,
        )

    test_session.add_all(
        [post(f"Post {i}", i, [python_tag, web_tag]) for i in range(1, 6)]
        + [
            post("Only Python", 6, [python_tag]),
            post("Draft", 0, [python_tag, web_tag], status=PostStatus.DRAFT),
            post("Deleted", 0, [python_tag, web_tag], deleted_at=now),
        ]
    )
    await test_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("field, total_count", [
    ("posts(page: 2, limit: 2)", 6),
    ('postsByTag(tagSlug: "web", page: 2, limit: 2)', 5),
    ('postsByTags(tagSlugs: ["python", "web"], requireAll: true, page: 2, limit: 2)', 5),
    ('postsByTags(tagSlugs: ["python", "web"], requireAll: false, page: 2, limit: 2)', 6),
], ids=["posts", "postsByTag", "postsByTags-all", "postsByTags-any"])
async def test_second_page(client: AsyncClient, tagged_posts, field, total_count):
    response = await client.post("/graphql", json={"query": f"{{ result: {field} {{ {PAGE_FIELDS} }} }}"})

    data = response.json()
    assert "errors" not in data, data["errors"]
    result = data["data"]["result"]
    assert [edge["node"]["title"] for edge in result["edges"]] == ["Post 3", "Post 4"]
    assert result["pageInfo"] == {
        "hasNextPage": True,
        "hasPreviousPage": True,
        "totalCount": total_count,
        "currentPage": 2,
        "totalPages": 3,
    }
