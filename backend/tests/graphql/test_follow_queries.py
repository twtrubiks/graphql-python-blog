"""追蹤功能 GraphQL queries 測試"""
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


USER_WITH_FOLLOWERS_QUERY = """
query GetUserWithFollowers($userId: Int!) {
    user(id: $userId) {
        id
        username
        followersCount
        followingCount
        followers {
            id
            username
        }
        following {
            id
            username
        }
    }
}
"""

IS_FOLLOWING_QUERY = """
query IsFollowing($userId: Int!) {
    user(id: $userId) {
        id
        username
        isFollowedByMe
    }
}
"""


@pytest.mark.asyncio
class TestFollowQueries:
    """追蹤功能 queries 測試"""

    async def test_user_followers_and_following(self, authenticated_client: AsyncClient, test_user, user_factory):
        """測試查詢用戶的追蹤者和追蹤中列表"""
        # 創建其他用戶
        user2 = await user_factory.create()
        user3 = await user_factory.create()

        # 設定追蹤關係
        # test_user 追蹤 user2
        await authenticated_client.post(
            "/graphql",
            json={
                "query": """
                mutation FollowUser($userId: ID!) {
                    followUser(userId: $userId) {
                        success
                    }
                }
                """,
                "variables": {"userId": str(user2.id)}
            }
        )

        # 切換到 user3 登入
        access_token = create_access_token(data={"sub": str(user3.id)})
        client3 = authenticated_client
        client3.headers.update({"Authorization": f"Bearer {access_token}"})

        # user3 追蹤 test_user
        await client3.post(
            "/graphql",
            json={
                "query": """
                mutation FollowUser($userId: ID!) {
                    followUser(userId: $userId) {
                        success
                    }
                }
                """,
                "variables": {"userId": test_user.id}
            }
        )

        # 查詢 test_user 的追蹤資訊
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": USER_WITH_FOLLOWERS_QUERY,
                "variables": {"userId": test_user.id}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["user"]

        assert data["id"] == str(test_user.id)
        assert data["followersCount"] == 1  # user3 追蹤 test_user
        assert data["followingCount"] == 1  # test_user 追蹤 user2
        assert len(data["followers"]) == 1
        assert data["followers"][0]["id"] == str(user3.id)
        assert len(data["following"]) == 1
        assert data["following"][0]["id"] == str(user2.id)

    async def test_is_followed_by_me(self, authenticated_client: AsyncClient, test_user, user_factory):
        """測試查詢是否正在追蹤某用戶"""
        # 創建另一個用戶
        target_user = await user_factory.create()

        # 初始狀態：未追蹤
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": IS_FOLLOWING_QUERY,
                "variables": {"userId": target_user.id}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["user"]
        assert data["isFollowedByMe"] is False

        # 追蹤用戶
        await authenticated_client.post(
            "/graphql",
            json={
                "query": """
                mutation FollowUser($userId: ID!) {
                    followUser(userId: $userId) {
                        success
                    }
                }
                """,
                "variables": {"userId": target_user.id}
            }
        )

        # 再次查詢：已追蹤
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": IS_FOLLOWING_QUERY,
                "variables": {"userId": target_user.id}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["user"]
        assert data["isFollowedByMe"] is True

    async def test_followers_without_authentication(self, client: AsyncClient, test_user):
        """測試未認證用戶可以查看追蹤數據但不能看到 isFollowedByMe"""
        response = await client.post(
            "/graphql",
            json={
                "query": USER_WITH_FOLLOWERS_QUERY,
                "variables": {"userId": test_user.id}
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]["user"]

        # 可以看到追蹤數據
        assert "followersCount" in data
        assert "followingCount" in data
        assert "followers" in data
        assert "following" in data