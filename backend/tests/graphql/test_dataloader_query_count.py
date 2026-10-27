"""DataLoader 失效（退化成 N+1）時輸出完全相同，只有 SQL 次數變多，所以直接數 SQL"""
import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post, PostStatus
from app.models.tag import Tag


POSTS_QUERY = """
query Posts($limit: Int!) {
    posts(limit: $limit) {
        edges {
            node {
                title
                tags { name }
                comments { content }
                totalComments
                likesCount
                isLiked
                author { username followersCount followingCount }
            }
        }
    }
}
"""


async def count_queries(client: AsyncClient, engine: AsyncEngine, query: str, **variables) -> int:
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        response = await client.post("/graphql", json={"query": query, "variables": variables})
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)

    data = response.json()
    assert "errors" not in data, data["errors"]
    return len(statements)


@pytest.fixture
async def posts_with_relations(test_session: AsyncSession, test_user):
    """5 篇已發布文章，各有標籤、留言與按讚"""
    tag = Tag(name="python", slug="python")
    posts = [
        Post(title=f"Post {i}", slug=f"post-{i}", content="content",
             status=PostStatus.PUBLISHED, author_id=test_user.id, tags=[tag])
        for i in range(5)
    ]
    test_session.add_all(posts)
    await test_session.flush()
    for post in posts:
        test_session.add_all([
            Comment(content="留言", user_id=test_user.id, post_id=post.id),
            Like(user_id=test_user.id, post_id=post.id),
        ])
    await test_session.commit()


@pytest.mark.asyncio
async def test_query_count_does_not_grow_with_posts(
    authenticated_client: AsyncClient, test_engine: AsyncEngine, posts_with_relations
):
    """每個欄位都由 DataLoader 批次載入：1 篇和 5 篇的 SQL 次數相同"""
    one = await count_queries(authenticated_client, test_engine, POSTS_QUERY, limit=1)
    five = await count_queries(authenticated_client, test_engine, POSTS_QUERY, limit=5)

    assert five == one


@pytest.mark.asyncio
async def test_preloaded_tags_need_no_query(
    authenticated_client: AsyncClient, test_engine: AsyncEngine, posts_with_relations
):
    """列表查詢已經 selectinload 標籤，tags 欄位不需要再查資料庫"""
    with_tags = await count_queries(authenticated_client, test_engine, "{ posts { edges { node { title tags { name } } } } }")
    without_tags = await count_queries(authenticated_client, test_engine, "{ posts { edges { node { title } } } }")

    assert with_tags == without_tags


@pytest.mark.asyncio
async def test_preloaded_author_needs_no_query(
    authenticated_client: AsyncClient, test_engine: AsyncEngine, posts_with_relations
):
    """列表查詢已經 joinedload 作者，author 欄位不需要再查資料庫"""
    with_author = await count_queries(
        authenticated_client, test_engine, "{ posts { edges { node { title author { username } } } } }"
    )
    without_author = await count_queries(authenticated_client, test_engine, "{ posts { edges { node { title } } } }")

    assert with_author == without_author


SEARCH_QUERY = """
query Search($term: String!) {
    search(term: $term) {
        ... on PostType { title author { username } tags { name } }
    }
}
"""


@pytest.mark.asyncio
async def test_search_query_count_does_not_grow_with_posts(
    client: AsyncClient, test_engine: AsyncEngine, test_session: AsyncSession, user_factory
):
    """搜尋結果沒有預載作者與標籤，要靠 DataLoader 批次載入：搜到 1 篇和 5 篇的 SQL 次數相同"""
    authors = [await user_factory.create() for _ in range(5)]
    test_session.add_all([
        Post(title=f"Searchable {i}", slug=f"searchable-{i}", content="content",
             status=PostStatus.PUBLISHED, author_id=author.id, tags=[Tag(name=f"tag-{i}", slug=f"tag-{i}")])
        for i, author in enumerate(authors)
    ])
    await test_session.commit()

    one = await count_queries(client, test_engine, SEARCH_QUERY, term="Searchable 0")
    five = await count_queries(client, test_engine, SEARCH_QUERY, term="Searchable")

    assert five == one
