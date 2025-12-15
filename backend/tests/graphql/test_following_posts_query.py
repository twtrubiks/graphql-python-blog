"""
測試 followingPosts Query

追蹤用戶文章列表查詢測試：
- 認證用戶可以查詢追蹤用戶的文章
- 未認證用戶無法查詢
- 分頁功能
"""

import pytest
from tests.factories import UserFactory, PostFactory
from app.models.follow import Follow
from app.models.post import PostStatus


class TestFollowingPostsQuery:
    """測試 followingPosts Query"""

    FOLLOWING_POSTS_QUERY = """
        query FollowingPosts($page: Int, $limit: Int) {
            followingPosts(page: $page, limit: $limit) {
                edges {
                    node {
                        id
                        title
                        slug
                        author {
                            id
                            username
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    totalCount
                    currentPage
                    totalPages
                }
            }
        }
    """

    @pytest.mark.asyncio
    async def test_following_posts_authenticated(
        self, authenticated_client, test_session, test_user
    ):
        """測試認證用戶可以查詢追蹤用戶的文章"""
        # Arrange: 建立被追蹤的作者和文章
        author = await UserFactory.create(test_session, username="followed_author")

        # test_user 追蹤 author
        test_session.add(Follow(follower_id=test_user.id, followed_id=author.id))

        # author 發布文章
        post = await PostFactory.create(
            test_session,
            author_id=author.id,
            title="Followed Author Post",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": self.FOLLOWING_POSTS_QUERY,
                "variables": {"page": 1, "limit": 10}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        result = data["data"]["followingPosts"]
        assert result["pageInfo"]["totalCount"] == 1
        assert len(result["edges"]) == 1
        assert result["edges"][0]["node"]["title"] == "Followed Author Post"
        assert result["edges"][0]["node"]["author"]["username"] == "followed_author"

    @pytest.mark.asyncio
    async def test_following_posts_unauthenticated(self, client):
        """測試未認證用戶無法查詢"""
        # Act
        response = await client.post(
            "/graphql",
            json={
                "query": self.FOLLOWING_POSTS_QUERY,
                "variables": {"page": 1, "limit": 10}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        # 可能是 "not authenticated" 或 "Authentication required"
        error_msg = data["errors"][0]["message"].lower()
        assert "authentic" in error_msg

    @pytest.mark.asyncio
    async def test_following_posts_pagination(
        self, authenticated_client, test_session, test_user
    ):
        """測試分頁功能"""
        # Arrange: 建立被追蹤的作者和多篇文章
        author = await UserFactory.create(test_session, username="prolific_author")

        # test_user 追蹤 author
        test_session.add(Follow(follower_id=test_user.id, followed_id=author.id))

        # author 發布 5 篇文章
        for i in range(5):
            await PostFactory.create(
                test_session,
                author_id=author.id,
                title=f"Post {i+1}",
                status=PostStatus.PUBLISHED
            )
        await test_session.commit()

        # Act: 查詢第一頁（2 篇）
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": self.FOLLOWING_POSTS_QUERY,
                "variables": {"page": 1, "limit": 2}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        result = data["data"]["followingPosts"]
        assert result["pageInfo"]["totalCount"] == 5
        assert result["pageInfo"]["totalPages"] == 3
        assert result["pageInfo"]["hasNextPage"] is True
        assert result["pageInfo"]["hasPreviousPage"] is False
        assert len(result["edges"]) == 2

    @pytest.mark.asyncio
    async def test_following_posts_no_following(
        self, authenticated_client, test_session, test_user
    ):
        """測試沒有追蹤任何人時返回空列表"""
        # Act: 不追蹤任何人直接查詢
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": self.FOLLOWING_POSTS_QUERY,
                "variables": {"page": 1, "limit": 10}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        result = data["data"]["followingPosts"]
        assert result["pageInfo"]["totalCount"] == 0
        assert len(result["edges"]) == 0

    @pytest.mark.asyncio
    async def test_following_posts_excludes_draft(
        self, authenticated_client, test_session, test_user
    ):
        """測試不會返回草稿文章"""
        # Arrange
        author = await UserFactory.create(test_session, username="draft_author")

        # test_user 追蹤 author
        test_session.add(Follow(follower_id=test_user.id, followed_id=author.id))

        # author 發布一篇文章和一篇草稿
        await PostFactory.create(
            test_session,
            author_id=author.id,
            title="Published Post",
            status=PostStatus.PUBLISHED
        )
        await PostFactory.create(
            test_session,
            author_id=author.id,
            title="Draft Post",
            status=PostStatus.DRAFT
        )
        await test_session.commit()

        # Act
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": self.FOLLOWING_POSTS_QUERY,
                "variables": {"page": 1, "limit": 10}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        result = data["data"]["followingPosts"]
        assert result["pageInfo"]["totalCount"] == 1
        assert result["edges"][0]["node"]["title"] == "Published Post"
