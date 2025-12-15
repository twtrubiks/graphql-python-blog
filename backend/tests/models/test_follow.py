"""Follow 模型測試"""
import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.follow import Follow


@pytest.mark.asyncio
class TestFollowModel:
    """Follow 模型測試類"""

    async def test_create_follow_success(self, test_session, user_factory):
        """測試成功創建追蹤關係"""
        # 創建兩個用戶
        follower = await user_factory.create()
        followed = await user_factory.create()

        # 創建追蹤關係
        follow = Follow(
            follower_id=follower.id,
            followed_id=followed.id
        )
        test_session.add(follow)
        await test_session.commit()
        await test_session.refresh(follow)

        # 驗證
        assert follow.id is not None
        assert follow.follower_id == follower.id
        assert follow.followed_id == followed.id
        assert isinstance(follow.created_at, datetime)

    async def test_follow_unique_constraint(self, test_session, user_factory):
        """測試唯一性約束（同一用戶不能重複追蹤）"""
        # 創建兩個用戶
        follower = await user_factory.create()
        followed = await user_factory.create()

        # 創建第一個追蹤關係
        follow1 = Follow(
            follower_id=follower.id,
            followed_id=followed.id
        )
        test_session.add(follow1)
        await test_session.commit()

        # 嘗試創建重複的追蹤關係
        follow2 = Follow(
            follower_id=follower.id,
            followed_id=followed.id
        )
        test_session.add(follow2)

        with pytest.raises(IntegrityError):
            await test_session.commit()

    async def test_cannot_follow_self(self, test_session, user_factory):
        """測試用戶不能追蹤自己"""
        user = await user_factory.create()

        # 嘗試創建自我追蹤
        follow = Follow(
            follower_id=user.id,
            followed_id=user.id
        )
        test_session.add(follow)

        # 應該拋出約束錯誤
        with pytest.raises(IntegrityError):
            await test_session.commit()

    async def test_follow_relationships(self, test_session, user_factory):
        """測試追蹤關係的外鍵關聯"""
        # 創建三個用戶
        user1 = await user_factory.create()
        user2 = await user_factory.create()
        user3 = await user_factory.create()

        # 創建追蹤關係
        # user1 追蹤 user2 和 user3
        follow1 = Follow(follower_id=user1.id, followed_id=user2.id)
        follow2 = Follow(follower_id=user1.id, followed_id=user3.id)
        # user2 追蹤 user1
        follow3 = Follow(follower_id=user2.id, followed_id=user1.id)

        test_session.add_all([follow1, follow2, follow3])
        await test_session.commit()

        # 查詢驗證
        # user1 的追蹤
        result = await test_session.execute(
            select(Follow).where(Follow.follower_id == user1.id)
        )
        user1_following = result.scalars().all()
        assert len(user1_following) == 2

        # user1 的追蹤者
        result = await test_session.execute(
            select(Follow).where(Follow.followed_id == user1.id)
        )
        user1_followers = result.scalars().all()
        assert len(user1_followers) == 1
        assert user1_followers[0].follower_id == user2.id

    async def test_cascade_delete(self, test_session, user_factory):
        """測試級聯刪除（刪除用戶時刪除相關追蹤關係）"""
        # 創建用戶和追蹤關係
        user1 = await user_factory.create()
        user2 = await user_factory.create()

        follow = Follow(follower_id=user1.id, followed_id=user2.id)
        test_session.add(follow)
        await test_session.commit()

        # 刪除用戶
        await test_session.delete(user1)
        await test_session.commit()

        # 驗證追蹤關係也被刪除
        result = await test_session.execute(
            select(Follow).where(
                (Follow.follower_id == user1.id) |
                (Follow.followed_id == user1.id)
            )
        )
        follows = result.scalars().all()
        assert len(follows) == 0