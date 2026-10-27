"""透過 createPost / updatePost 設定文章標籤"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.tag import Tag


CREATE_POST_MUTATION = """
mutation CreatePost($input: PostInput!) {
    createPost(input: $input) {
        id
        tags { name slug }
    }
}
"""

UPDATE_POST_MUTATION = """
mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
    updatePost(id: $id, input: $input) {
        tags { name slug }
        updatedAt
    }
}
"""

POST_TAGS_QUERY = "query GetPost($id: ID!) { post(id: $id) { tags { name slug } } }"
ALL_TAGS_QUERY = "{ tags { name slug } }"


async def create_post(client: AsyncClient, tags) -> dict:
    response = await client.post(
        "/graphql",
        json={
            "query": CREATE_POST_MUTATION,
            "variables": {"input": {"title": "Tagged Post", "content": "content", "tags": tags}}
        }
    )
    data = response.json()
    assert "errors" not in data, data["errors"]
    return data["data"]["createPost"]


async def graphql(client: AsyncClient, query: str, **variables) -> dict:
    response = await client.post("/graphql", json={"query": query, "variables": variables})
    data = response.json()
    assert "errors" not in data, data["errors"]
    return data["data"]


def sorted_tags(tags: list[dict]) -> list[dict]:
    return sorted(tags, key=lambda tag: tag["slug"])


@pytest.mark.asyncio
class TestCreatePostWithTags:
    async def test_creates_new_tags(self, authenticated_client: AsyncClient):
        """新標籤會被建立；名稱去除空白、空字串略過、slug 相同的只算一個"""
        post = await create_post(authenticated_client, ["Python", "  GraphQL  ", "", "python"])

        expected = [{"name": "GraphQL", "slug": "graphql"}, {"name": "Python", "slug": "python"}]
        assert sorted_tags(post["tags"]) == expected

        # 用新的請求確認標籤與關聯都已寫入
        saved = await graphql(authenticated_client, POST_TAGS_QUERY, id=post["id"])
        assert sorted_tags(saved["post"]["tags"]) == expected
        assert (await graphql(authenticated_client, ALL_TAGS_QUERY))["tags"] == expected

    async def test_reuses_existing_tag(self, authenticated_client: AsyncClient, test_session: AsyncSession):
        """slug 相同的既有標籤直接沿用，不會重複建立"""
        test_session.add(Tag(name="python", slug="python"))
        await test_session.commit()

        post = await create_post(authenticated_client, ["Python"])

        assert post["tags"] == [{"name": "python", "slug": "python"}]
        assert (await graphql(authenticated_client, ALL_TAGS_QUERY))["tags"] == [
            {"name": "python", "slug": "python"}
        ]

    async def test_without_tags(self, authenticated_client: AsyncClient):
        post = await create_post(authenticated_client, None)

        assert post["tags"] == []


@pytest.mark.asyncio
class TestUpdatePostTags:
    async def test_replace_tags(self, authenticated_client: AsyncClient):
        post = await create_post(authenticated_client, ["python", "web"])

        updated = await graphql(
            authenticated_client, UPDATE_POST_MUTATION, id=post["id"], input={"tags": ["rust"]}
        )

        assert updated["updatePost"]["tags"] == [{"name": "rust", "slug": "rust"}]
        saved = await graphql(authenticated_client, POST_TAGS_QUERY, id=post["id"])
        assert saved["post"]["tags"] == [{"name": "rust", "slug": "rust"}]

    async def test_tags_only_update_changes_updated_at(
        self, authenticated_client: AsyncClient, test_session: AsyncSession, test_user
    ):
        """只改標籤時 posts 這一列沒有變動，onupdate 不會觸發，updatedAt 要由 update_post 自己設定"""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        post = Post(title="Old Post", slug="old-post", content="content", author_id=test_user.id, updated_at=yesterday)
        test_session.add(post)
        await test_session.commit()

        updated = await graphql(authenticated_client, UPDATE_POST_MUTATION, id=str(post.id), input={"tags": ["rust"]})

        assert datetime.fromisoformat(updated["updatePost"]["updatedAt"]) > yesterday + timedelta(hours=23)

    async def test_empty_list_clears_tags(self, authenticated_client: AsyncClient):
        post = await create_post(authenticated_client, ["python"])

        updated = await graphql(
            authenticated_client, UPDATE_POST_MUTATION, id=post["id"], input={"tags": []}
        )

        assert updated["updatePost"]["tags"] == []
        saved = await graphql(authenticated_client, POST_TAGS_QUERY, id=post["id"])
        assert saved["post"]["tags"] == []

    async def test_omitted_tags_unchanged(self, authenticated_client: AsyncClient):
        """沒有傳 tags 時保留原本的標籤"""
        post = await create_post(authenticated_client, ["python"])

        updated = await graphql(
            authenticated_client, UPDATE_POST_MUTATION, id=post["id"], input={"title": "New Title"}
        )

        assert updated["updatePost"]["tags"] == [{"name": "python", "slug": "python"}]
