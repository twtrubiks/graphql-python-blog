import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from app.models.like import Like
from app.models.post import Post


@pytest.mark.asyncio
class TestLikePostMutation:
    """測試按讚文章 mutation"""

    async def test_like_post_success(self, authenticated_client: AsyncClient, test_post):
        """測試成功按讚文章"""
        mutation = """
        mutation LikePost($postId: ID!) {
            likePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": str(test_post.id)}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()["data"]["likePost"]

        assert data["success"] is True
        assert data["message"] == "按讚成功"

    async def test_like_post_twice_fails(self, authenticated_client: AsyncClient, test_post):
        """測試重複按讚會失敗"""
        mutation = """
        mutation LikePost($postId: ID!) {
            likePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": str(test_post.id)}

        # 第一次按讚
        response1 = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        assert response1.status_code == 200
        assert response1.json()["data"]["likePost"]["success"] is True

        # 第二次按讚（應該失敗）
        response2 = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        assert response2.status_code == 200
        data = response2.json()["data"]["likePost"]
        assert data["success"] is False
        assert "已經按讚" in data["message"] or "already liked" in data["message"].lower()

    async def test_like_nonexistent_post(self, authenticated_client: AsyncClient):
        """測試按讚不存在的文章"""
        mutation = """
        mutation LikePost($postId: ID!) {
            likePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": "999999"}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower()

    async def test_like_soft_deleted_post_fails(self, authenticated_client: AsyncClient, test_session, test_post):
        """測試按讚已軟刪除的文章會失敗"""
        post = await test_session.get(Post, test_post.id)
        post.deleted_at = datetime.now(timezone.utc)
        await test_session.commit()

        mutation = """
        mutation LikePost($postId: ID!) {
            likePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": str(test_post.id)}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower()

    async def test_like_post_without_auth(self, client: AsyncClient, test_post):
        """測試未登入無法按讚"""
        mutation = """
        mutation LikePost($postId: ID!) {
            likePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": str(test_post.id)}

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "登入" in errors[0]["message"] or "authentication" in errors[0]["message"].lower()


@pytest.mark.asyncio
class TestUnlikePostMutation:
    """測試取消按讚 mutation"""

    async def test_unlike_post_success(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """測試成功取消按讚"""
        # 先按讚
        like = Like(
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add(like)
        await test_session.commit()

        mutation = """
        mutation UnlikePost($postId: ID!) {
            unlikePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": str(test_post.id)}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()["data"]["unlikePost"]

        assert data["success"] is True
        assert data["message"] == "取消按讚成功"

    async def test_unlike_not_liked_post(self, authenticated_client: AsyncClient, test_post):
        """測試取消未按讚的文章"""
        mutation = """
        mutation UnlikePost($postId: ID!) {
            unlikePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": str(test_post.id)}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()["data"]["unlikePost"]
        assert data["success"] is False
        assert "沒有按讚" in data["message"] or "not liked" in data["message"].lower()

    async def test_unlike_nonexistent_post(self, authenticated_client: AsyncClient):
        """測試取消按讚不存在的文章"""
        mutation = """
        mutation UnlikePost($postId: ID!) {
            unlikePost(postId: $postId) {
                success
                message
            }
        }
        """

        variables = {"postId": "999999"}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower()