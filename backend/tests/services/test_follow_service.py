"""FollowService 擴展功能測試

測試 get_follower_ids 和 get_following_ids 方法
"""

import pytest
from tests.factories import UserFactory
from app.services.follow import FollowService
from app.models.follow import Follow
from tests.utils import insert_after_existence_check


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


class TestFollowServiceCounts:
    """沒有 DataLoader 時，followersCount / followingCount 改用這兩個方法直接查詢"""

    @pytest.mark.asyncio
    async def test_followers_and_following_count(self, test_session):
        # alice 被 bob、carol 追蹤，自己追蹤 bob；dave 沒有任何追蹤關係
        alice = await UserFactory.create(test_session, username="alice")
        bob = await UserFactory.create(test_session, username="bob")
        carol = await UserFactory.create(test_session, username="carol")
        dave = await UserFactory.create(test_session, username="dave")
        test_session.add_all([
            Follow(follower_id=bob.id, followed_id=alice.id),
            Follow(follower_id=carol.id, followed_id=alice.id),
            Follow(follower_id=alice.id, followed_id=bob.id),
        ])
        await test_session.commit()

        counts = {
            user.username: (
                await FollowService.get_followers_count(test_session, user.id),
                await FollowService.get_following_count(test_session, user.id),
            )
            for user in (alice, bob, carol, dave)
        }

        assert counts == {"alice": (2, 1), "bob": (1, 1), "carol": (0, 1), "dave": (0, 0)}


class TestFollowUserRace:
    @pytest.mark.asyncio
    async def test_follow_race_is_blocked_by_unique_constraint(self, test_session, test_engine, monkeypatch):
        """同時送出兩次追蹤：兩邊都查不到既有的追蹤，後寫入的那個要回報失敗，而不是拋出錯誤"""
        alice = await UserFactory.create(test_session)
        bob = await UserFactory.create(test_session)
        await test_session.commit()
        alice_id, bob_id = alice.id, bob.id  # rollback 會讓 ORM 物件過期，之後不能再讀屬性
        insert_after_existence_check(
            monkeypatch, test_session, test_engine, Follow(follower_id=alice_id, followed_id=bob_id)
        )

        result = await FollowService.follow_user(test_session, alice_id, bob_id)

        assert result == (False, "Failed to follow user", None)
        # rollback 之後 session 還能繼續使用，而且只有一筆追蹤
        assert await FollowService.get_followers_count(test_session, bob_id) == 1
