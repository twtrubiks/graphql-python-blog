"""FollowService 擴展功能測試

測試 get_follower_ids 和 get_following_ids 方法
"""

import pytest
from tests.factories import UserFactory
from app.services.follow import FollowService
from app.models.follow import Follow


class TestFollowServiceGetIds:
    """測試 FollowService 的 ID 列表查詢方法"""

    @pytest.mark.asyncio
    async def test_get_follower_ids_with_followers(self, test_session):
        """測試有追蹤者時獲取追蹤者 ID 列表"""
        # Arrange: 建立 3 個用戶，user2 和 user3 追蹤 user1
        user1 = await UserFactory.create(test_session, username="user1")
        user2 = await UserFactory.create(test_session, username="user2")
        user3 = await UserFactory.create(test_session, username="user3")

        # 建立追蹤關係
        follow1 = Follow(follower_id=user2.id, followed_id=user1.id)
        follow2 = Follow(follower_id=user3.id, followed_id=user1.id)
        test_session.add_all([follow1, follow2])
        await test_session.commit()

        # Act: 獲取 user1 的追蹤者 ID 列表
        follower_ids = await FollowService.get_follower_ids(test_session, user1.id)

        # Assert
        assert len(follower_ids) == 2
        assert user2.id in follower_ids
        assert user3.id in follower_ids

    @pytest.mark.asyncio
    async def test_get_follower_ids_no_followers(self, test_session):
        """測試沒有追蹤者時返回空列表"""
        # Arrange: 建立一個沒有追蹤者的用戶
        user = await UserFactory.create(test_session, username="lonely_user")
        await test_session.commit()

        # Act
        follower_ids = await FollowService.get_follower_ids(test_session, user.id)

        # Assert
        assert follower_ids == []

    @pytest.mark.asyncio
    async def test_get_following_ids_with_following(self, test_session):
        """測試有追蹤中時獲取追蹤中 ID 列表"""
        # Arrange: user1 追蹤 user2 和 user3
        user1 = await UserFactory.create(test_session, username="follower_user")
        user2 = await UserFactory.create(test_session, username="followed_user1")
        user3 = await UserFactory.create(test_session, username="followed_user2")

        # 建立追蹤關係
        follow1 = Follow(follower_id=user1.id, followed_id=user2.id)
        follow2 = Follow(follower_id=user1.id, followed_id=user3.id)
        test_session.add_all([follow1, follow2])
        await test_session.commit()

        # Act: 獲取 user1 追蹤的人的 ID 列表
        following_ids = await FollowService.get_following_ids(test_session, user1.id)

        # Assert
        assert len(following_ids) == 2
        assert user2.id in following_ids
        assert user3.id in following_ids

    @pytest.mark.asyncio
    async def test_get_following_ids_no_following(self, test_session):
        """測試沒有追蹤任何人時返回空列表"""
        # Arrange: 建立一個沒有追蹤任何人的用戶
        user = await UserFactory.create(test_session, username="not_following_anyone")
        await test_session.commit()

        # Act
        following_ids = await FollowService.get_following_ids(test_session, user.id)

        # Assert
        assert following_ids == []

    @pytest.mark.asyncio
    async def test_get_follower_ids_does_not_include_following(self, test_session):
        """測試 get_follower_ids 不會返回該用戶追蹤的人"""
        # Arrange: user1 追蹤 user2，user2 也追蹤 user1
        user1 = await UserFactory.create(test_session, username="mutual_user1")
        user2 = await UserFactory.create(test_session, username="mutual_user2")

        # user1 追蹤 user2
        follow1 = Follow(follower_id=user1.id, followed_id=user2.id)
        # user2 追蹤 user1
        follow2 = Follow(follower_id=user2.id, followed_id=user1.id)
        test_session.add_all([follow1, follow2])
        await test_session.commit()

        # Act: 獲取 user1 的追蹤者（應該只有 user2）
        follower_ids = await FollowService.get_follower_ids(test_session, user1.id)

        # Assert: 只有 user2 追蹤 user1
        assert len(follower_ids) == 1
        assert user2.id in follower_ids

    @pytest.mark.asyncio
    async def test_get_following_ids_does_not_include_followers(self, test_session):
        """測試 get_following_ids 不會返回追蹤該用戶的人"""
        # Arrange: user1 追蹤 user2，user3 追蹤 user1
        user1 = await UserFactory.create(test_session, username="test_user1")
        user2 = await UserFactory.create(test_session, username="test_user2")
        user3 = await UserFactory.create(test_session, username="test_user3")

        # user1 追蹤 user2
        follow1 = Follow(follower_id=user1.id, followed_id=user2.id)
        # user3 追蹤 user1
        follow2 = Follow(follower_id=user3.id, followed_id=user1.id)
        test_session.add_all([follow1, follow2])
        await test_session.commit()

        # Act: 獲取 user1 追蹤的人（應該只有 user2）
        following_ids = await FollowService.get_following_ids(test_session, user1.id)

        # Assert: user1 只追蹤 user2，不應包含 user3
        assert len(following_ids) == 1
        assert user2.id in following_ids
        assert user3.id not in following_ids
