"""
列表查詢的參數預設值與「沒有符合的文章」

前端每次都明確傳入分頁參數，這些預設值是給其他客戶端（例如 GraphiQL）的 API 契約：
沒傳 page / limit 時是第 1 頁、每頁 10 篇，沒傳 requireAll 時是「任一標籤」。
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.follow import Follow
from app.models.post import Post, PostStatus
from app.models.tag import Tag

PAGE_INFO = "pageInfo { currentPage totalCount totalPages hasNextPage hasPreviousPage }"

LIST_QUERIES = {
    "posts": "posts",
    "postsByTag": 'postsByTag(tagSlug: "python")',
    "postsByTags": 'postsByTags(tagSlugs: ["python"])',
    "followingPosts": "followingPosts",
    "myPosts": "myPosts",
    "postsByAuthor": 'postsByAuthor(authorUsername: "author")',
}


def list_query(field: str) -> str:
    return f"{{ {LIST_QUERIES[field]} {{ edges {{ node {{ title }} }} {PAGE_INFO} }} }}"


async def query_as(client: AsyncClient, user, query: str) -> dict:
    token = create_access_token(data={"sub": str(user.id)})
    response = await client.post("/graphql", json={"query": query}, headers={"Authorization": f"Bearer {token}"})
    data = response.json()
    assert "errors" not in data, data["errors"]
    return data["data"]


@pytest.fixture
async def author(test_session, test_user, user_factory):
    """test_user 追蹤的作者"""
    author = await user_factory.create(username="author")
    test_session.add(Follow(follower_id=test_user.id, followed_id=author.id))
    await test_session.commit()
    return author


def python_posts(author, count: int, status=PostStatus.PUBLISHED):
    tag = Tag(name="python", slug="python")
    return [
        Post(title=f"Post {i}", slug=f"post-{i}", content="content", status=status,
             author_id=author.id, tags=[tag])
        for i in range(count)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("field", LIST_QUERIES)
async def test_list_queries_default_to_first_page_of_ten(
    client: AsyncClient, test_session, test_user, author, field
):
    test_session.add_all(python_posts(author, 11))
    await test_session.commit()
    # myPosts 以作者本人查詢，其餘（包括 followingPosts）以追蹤者查詢
    viewer = author if field == "myPosts" else test_user

    result = (await query_as(client, viewer, list_query(field)))[field]

    assert len(result["edges"]) == 10
    assert result["pageInfo"] == {
        "currentPage": 1, "totalCount": 11, "totalPages": 2, "hasNextPage": True, "hasPreviousPage": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["posts", "postsByTag", "postsByTags", "followingPosts", "postsByAuthor"])
async def test_list_queries_with_only_drafts(client: AsyncClient, test_session, test_user, author, field):
    """標籤與作者都存在，但只有草稿：不能列出，總數與頁數都是 0"""
    test_session.add_all(python_posts(author, 2, status=PostStatus.DRAFT))
    await test_session.commit()

    result = (await query_as(client, test_user, list_query(field)))[field]

    assert result == {
        "edges": [],
        "pageInfo": {
            "currentPage": 1, "totalCount": 0, "totalPages": 0, "hasNextPage": False, "hasPreviousPage": False,
        },
    }


@pytest.mark.asyncio
async def test_posts_requiring_all_tags_with_only_drafts(client: AsyncClient, test_session, test_user, author):
    test_session.add_all(python_posts(author, 2, status=PostStatus.DRAFT))
    await test_session.commit()

    result = await query_as(
        client, test_user, '{ postsByTags(tagSlugs: ["python"], requireAll: true) { pageInfo { totalCount } } }'
    )

    assert result["postsByTags"]["pageInfo"]["totalCount"] == 0


@pytest.mark.asyncio
async def test_posts_by_tags_defaults_to_any_tag(client: AsyncClient, test_session, test_user, author):
    """沒傳 requireAll 時，含有任一標籤的文章都符合"""
    test_session.add_all([
        Post(title="Only Python", slug="only-python", content="content", status=PostStatus.PUBLISHED,
             author_id=author.id, tags=[Tag(name="python", slug="python")]),
        Post(title="Only Web", slug="only-web", content="content", status=PostStatus.PUBLISHED,
             author_id=author.id, tags=[Tag(name="web", slug="web")]),
    ])
    await test_session.commit()

    result = await query_as(
        client, test_user, '{ postsByTags(tagSlugs: ["python", "web"]) { edges { node { title } } } }'
    )

    titles = sorted(edge["node"]["title"] for edge in result["postsByTags"]["edges"])
    assert titles == ["Only Python", "Only Web"]
