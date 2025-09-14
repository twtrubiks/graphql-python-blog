"""追蹤功能 GraphQL mutations 測試"""
import pytest
from httpx import AsyncClient


FOLLOW_USER_MUTATION = """
mutation FollowUser($userId: ID!) {
    followUser(userId: $userId) {
        success
        message
        follow {
            id
            follower {
                id
                username
            }
            followed {
                id
                username
            }
            createdAt
        }
    }
}
"""

UNFOLLOW_USER_MUTATION = """
mutation UnfollowUser($userId: ID!) {
    unfollowUser(userId: $userId) {
        success
        message
    }
}
"""


@pytest.mark.asyncio
class TestFollowMutations:
    """追蹤功能 mutations 測試"""

    async def test_follow_user_success(self, authenticated_client: AsyncClient, user_factory, test_user):
        """測試成功追蹤用戶"""
        # 創建要追蹤的用戶
        target_user = await user_factory.create()

        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["followUser"]

        assert data["success"] is True
        assert data["message"] == "Successfully followed user"
        assert data["follow"]["follower"]["id"] == str(test_user.id)
        assert data["follow"]["followed"]["id"] == str(target_user.id)

    async def test_follow_user_already_following(self, authenticated_client: AsyncClient, user_factory, test_user):
        """測試重複追蹤同一用戶"""
        # 創建要追蹤的用戶
        target_user = await user_factory.create()

        # 第一次追蹤
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )
        assert response.status_code == 200
        assert response.json()["data"]["followUser"]["success"] is True

        # 第二次追蹤（應該失敗）
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data or (data["data"]["followUser"]["success"] is False)

    async def test_cannot_follow_self(self, authenticated_client: AsyncClient, test_user):
        """測試用戶不能追蹤自己"""
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": str(test_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data or (data["data"]["followUser"]["success"] is False)

    async def test_follow_non_existent_user(self, authenticated_client: AsyncClient):
        """測試追蹤不存在的用戶"""
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": "99999"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data or (data["data"]["followUser"]["success"] is False)

    async def test_follow_requires_authentication(self, client: AsyncClient, user_factory):
        """測試追蹤需要認證"""
        target_user = await user_factory.create()

        response = await client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()
        # 檢查是否有錯誤或成功標誌為 false
        assert "errors" in data or (data["data"]["followUser"]["success"] is False)

    async def test_unfollow_user_success(self, authenticated_client: AsyncClient, user_factory, test_user):
        """測試成功取消追蹤"""
        # 創建並追蹤用戶
        target_user = await user_factory.create()

        # 先追蹤
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": FOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )
        assert response.json()["data"]["followUser"]["success"] is True

        # 取消追蹤
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": UNFOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["unfollowUser"]
        assert data["success"] is True
        assert data["message"] == "Successfully unfollowed user"

    async def test_unfollow_not_following(self, authenticated_client: AsyncClient, user_factory):
        """測試取消追蹤未追蹤的用戶"""
        target_user = await user_factory.create()

        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": UNFOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data or (data["data"]["unfollowUser"]["success"] is False)

    async def test_unfollow_requires_authentication(self, client: AsyncClient, user_factory):
        """測試取消追蹤需要認證"""
        target_user = await user_factory.create()

        response = await client.post(
            "/graphql",
            json={
                "query": UNFOLLOW_USER_MUTATION,
                "variables": {"userId": str(target_user.id)}
            }
        )

        assert response.status_code == 200
        data = response.json()
        # 檢查是否有錯誤或成功標誌為 false
        assert "errors" in data or (data["data"]["unfollowUser"]["success"] is False)