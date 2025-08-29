"""測試文章標籤查詢功能"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.post import Post, PostStatus
from app.models.tag import Tag, post_tags


class TestPostTagsQuery:
    """測試文章標籤查詢"""

    @pytest.mark.asyncio
    async def test_post_with_tags_query(
        self,
        authenticated_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """測試查詢文章及其標籤"""
        # 創建文章
        post = Post(
            title="GraphQL Tutorial",
            slug="graphql-tutorial",
            content="Learn GraphQL step by step",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        test_session.add(post)

        # 創建標籤
        tag1 = Tag(name="graphql", slug="graphql")
        tag2 = Tag(name="tutorial", slug="tutorial")
        test_session.add_all([tag1, tag2])
        await test_session.commit()

        # 建立關聯
        await test_session.execute(
            post_tags.insert().values(post_id=post.id, tag_id=tag1.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post.id, tag_id=tag2.id)
        )
        await test_session.commit()

        # 查詢文章及其標籤
        query = """
        query GetPostWithTags($id: ID!) {
            post(id: $id) {
                id
                title
                tags {
                    id
                    name
                    slug
                }
            }
        }
        """

        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["post"]
        assert data["title"] == "GraphQL Tutorial"
        assert len(data["tags"]) == 2

        tag_names = {tag["name"] for tag in data["tags"]}
        assert "graphql" in tag_names
        assert "tutorial" in tag_names

    @pytest.mark.asyncio
    async def test_posts_list_with_tags(
        self,
        authenticated_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """測試查詢文章列表包含標籤"""
        # 創建多個文章和標籤
        post1 = Post(
            title="Post 1",
            slug="post-1",
            content="Content 1",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        post2 = Post(
            title="Post 2",
            slug="post-2",
            content="Content 2",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )

        tag1 = Tag(name="python", slug="python")
        tag2 = Tag(name="django", slug="django")

        test_session.add_all([post1, post2, tag1, tag2])
        await test_session.commit()

        # 建立關聯
        await test_session.execute(
            post_tags.insert().values(post_id=post1.id, tag_id=tag1.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post2.id, tag_id=tag1.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post2.id, tag_id=tag2.id)
        )
        await test_session.commit()

        # 查詢文章列表
        query = """
        query GetPostsWithTags {
            posts(limit: 10) {
                edges {
                    node {
                        id
                        title
                        tags {
                            name
                        }
                    }
                }
            }
        }
        """

        response = await authenticated_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        edges = response.json()["data"]["posts"]["edges"]

        # 驗證文章1有1個標籤
        post1_data = next(edge for edge in edges if edge["node"]["title"] == "Post 1")
        assert len(post1_data["node"]["tags"]) == 1
        assert post1_data["node"]["tags"][0]["name"] == "python"

        # 驗證文章2有2個標籤
        post2_data = next(edge for edge in edges if edge["node"]["title"] == "Post 2")
        assert len(post2_data["node"]["tags"]) == 2
        tag_names = {tag["name"] for tag in post2_data["node"]["tags"]}
        assert "python" in tag_names
        assert "django" in tag_names

    @pytest.mark.asyncio
    async def test_empty_tags_list(
        self,
        authenticated_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """測試沒有標籤的文章"""
        # 創建沒有標籤的文章
        post = Post(
            title="Post without tags",
            slug="post-without-tags",
            content="Content",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        test_session.add(post)
        await test_session.commit()

        # 查詢文章
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
                tags {
                    name
                }
            }
        }
        """

        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["post"]
        assert data["title"] == "Post without tags"
        assert data["tags"] == []