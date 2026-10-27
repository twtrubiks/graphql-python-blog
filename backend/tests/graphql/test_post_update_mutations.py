"""updatePost：改 slug，以及改狀態時的 publishedAt"""
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus


UPDATE_POST_MUTATION = """
mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
    updatePost(id: $id, input: $input) { slug status publishedAt }
}
"""

POST_BY_SLUG_QUERY = "query GetPost($slug: String!) { post(slug: $slug) { title } }"


async def graphql(client: AsyncClient, query: str, **variables) -> dict:
    response = await client.post("/graphql", json={"query": query, "variables": variables})
    return response.json()


async def update_post(client: AsyncClient, post: Post, **input) -> dict:
    data = await graphql(client, UPDATE_POST_MUTATION, id=str(post.id), input=input)
    assert "errors" not in data, data["errors"]
    return data["data"]["updatePost"]


@pytest.fixture
def make_post(test_session: AsyncSession, test_user):
    async def make(slug: str, status=PostStatus.DRAFT, published_at=None) -> Post:
        post = Post(
            title=slug, slug=slug, content="content",
            status=status, published_at=published_at, author_id=test_user.id,
        )
        test_session.add(post)
        await test_session.commit()
        return post
    return make


@pytest.mark.asyncio
class TestUpdateSlug:
    async def test_change_slug(self, authenticated_client: AsyncClient, make_post):
        post = await make_post("old-slug")

        assert (await update_post(authenticated_client, post, slug="new-slug"))["slug"] == "new-slug"

        # 用新的請求確認已寫入：新 slug 查得到，舊的查不到
        found = await graphql(authenticated_client, POST_BY_SLUG_QUERY, slug="new-slug")
        assert found["data"]["post"] == {"title": "old-slug"}
        gone = await graphql(authenticated_client, POST_BY_SLUG_QUERY, slug="old-slug")
        assert gone["data"]["post"] is None

    async def test_keep_own_slug(self, authenticated_client: AsyncClient, make_post):
        """送出文章原本的 slug 不算重複"""
        post = await make_post("same-slug")

        assert (await update_post(authenticated_client, post, slug="same-slug"))["slug"] == "same-slug"

    async def test_slug_taken_by_another_post(self, authenticated_client: AsyncClient, make_post):
        await make_post("taken")
        post = await make_post("mine")

        data = await graphql(authenticated_client, UPDATE_POST_MUTATION, id=str(post.id), input={"slug": "taken"})

        assert data["errors"][0]["message"] == "Slug already exists"


@pytest.mark.asyncio
@pytest.mark.parametrize("input, message", [
    ({"title": ""}, "Title cannot be empty"),
    ({"title": "   "}, "Title cannot be empty"),
    ({"content": ""}, "Content cannot be empty"),
    ({"content": "   "}, "Content cannot be empty"),
], ids=["empty-title", "blank-title", "empty-content", "blank-content"])
async def test_update_validation_errors(authenticated_client: AsyncClient, make_post, input, message):
    post = await make_post("original")

    data = await graphql(authenticated_client, UPDATE_POST_MUTATION, id=str(post.id), input=input)

    assert data["errors"][0]["message"] == message


@pytest.mark.asyncio
class TestUpdateStatusPublishedAt:
    async def test_publishing_draft_sets_published_at(self, authenticated_client: AsyncClient, make_post):
        post = await make_post("draft")

        updated = await update_post(authenticated_client, post, status="PUBLISHED")

        assert updated["status"] == "PUBLISHED"
        assert updated["publishedAt"] is not None

    async def test_editing_published_post_keeps_published_at(self, authenticated_client: AsyncClient, make_post):
        published_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        post = await make_post("published", PostStatus.PUBLISHED, published_at)

        updated = await update_post(authenticated_client, post, title="新標題", status="PUBLISHED")

        assert datetime.fromisoformat(updated["publishedAt"]) == published_at

    async def test_saving_draft_leaves_published_at_empty(self, authenticated_client: AsyncClient, make_post):
        post = await make_post("draft")

        updated = await update_post(authenticated_client, post, status="DRAFT")

        assert updated["publishedAt"] is None

    async def test_unpublishing_clears_published_at(self, authenticated_client: AsyncClient, make_post):
        """與 unpublishPost 一致：存成草稿就沒有發布時間，重新發布時設定新的時間"""
        published_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        post = await make_post("published", PostStatus.PUBLISHED, published_at)

        assert (await update_post(authenticated_client, post, status="DRAFT"))["publishedAt"] is None

        republished = await update_post(authenticated_client, post, status="PUBLISHED")
        assert datetime.fromisoformat(republished["publishedAt"]) > published_at
