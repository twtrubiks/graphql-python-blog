"""追蹤功能 GraphQL queries 測試"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from app.core.security import create_access_token
from app.models.follow import Follow
from app.models.user import User


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

        # 可以看到追蹤數據；沒有追蹤關係時數量是 0、列表是空的
        assert data["followersCount"] == 0
        assert data["followingCount"] == 0
        assert data["followers"] == []
        assert data["following"] == []
    async def test_lists_newest_first(self, client: AsyncClient, test_session, test_user, user_factory):
        """followers / following 由新到舊排列；同時建立的，id 較大（較晚寫入）的在前"""
        a, b, c = [await user_factory.create() for _ in range(3)]
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(minutes=1)
        # 依序寫入，id 遞增：a 與 b 同時，c 較早
        test_session.add_all([
            Follow(follower_id=a.id, followed_id=test_user.id, created_at=now),
            Follow(follower_id=b.id, followed_id=test_user.id, created_at=now),
            Follow(follower_id=c.id, followed_id=test_user.id, created_at=earlier),
            Follow(follower_id=test_user.id, followed_id=a.id, created_at=now),
            Follow(follower_id=test_user.id, followed_id=b.id, created_at=now),
            Follow(follower_id=test_user.id, followed_id=c.id, created_at=earlier),
        ])
        await test_session.commit()

        response = await client.post(
            "/graphql",
            json={"query": USER_WITH_FOLLOWERS_QUERY, "variables": {"userId": test_user.id}}
        )

        data = response.json()["data"]["user"]
        expected = [str(b.id), str(a.id), str(c.id)]
        assert [user["id"] for user in data["followers"]] == expected
        assert [user["id"] for user in data["following"]] == expected


@pytest.mark.asyncio
async def test_follow_lists_are_capped_at_100(client: AsyncClient, test_session, test_user):
    """追蹤者 / 追蹤中列表每人最多回傳 100 個（FOLLOW_LIST_LIMIT），計數不受限制"""
    fans = [User(email=f"fan{i}@example.com", username=f"fan{i}", hashed_password="unused") for i in range(101)]
    test_session.add_all(fans)
    await test_session.flush()
    test_session.add_all(
        [Follow(follower_id=fan.id, followed_id=test_user.id) for fan in fans]
        + [Follow(follower_id=test_user.id, followed_id=fan.id) for fan in fans]
    )
    await test_session.commit()

    response = await client.post("/graphql", json={
        "query": "query($id: Int!) { user(id: $id) { followersCount followingCount followers { id } following { id } } }",
        "variables": {"id": test_user.id},
    })

    data = response.json()["data"]["user"]
    assert (data["followersCount"], data["followingCount"]) == (101, 101)
    assert (len(data["followers"]), len(data["following"])) == (100, 100)

