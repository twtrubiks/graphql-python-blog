import pytest
from sqlalchemy.exc import IntegrityError
from app.models.like import Like


@pytest.mark.asyncio
class TestLikeModel:
    """Like 模型測試"""
    
    async def test_create_like_success(self, async_session, test_user, test_post):
        """測試成功創建按讚"""
        like = Like(
            user_id=test_user.id,
            post_id=test_post.id
        )
        
        async_session.add(like)
        await async_session.commit()
        await async_session.refresh(like)
        
        assert like.id is not None
        assert like.user_id == test_user.id
        assert like.post_id == test_post.id
        assert like.created_at is not None
    
    async def test_unique_user_post_constraint(self, async_session, test_user, test_post):
        """測試同一用戶不能重複按讚同一篇文章"""
        # 第一次按讚
        like1 = Like(
            user_id=test_user.id,
            post_id=test_post.id
        )
        async_session.add(like1)
        await async_session.commit()
        
        # 嘗試第二次按讚（應該失敗）
        like2 = Like(
            user_id=test_user.id,
            post_id=test_post.id
        )
        async_session.add(like2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    async def test_like_requires_user(self, async_session, test_post):
        """測試按讚必須有用戶"""
        like = Like(
            user_id=None,
            post_id=test_post.id
        )
        async_session.add(like)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    async def test_like_requires_post(self, async_session, test_user):
        """測試按讚必須有文章"""
        like = Like(
            user_id=test_user.id,
            post_id=None
        )
        async_session.add(like)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    async def test_cascade_delete_with_user(self, async_session, test_user, test_post):
        """測試用戶刪除時，相關按讚也會被刪除"""
        like = Like(
            user_id=test_user.id,
            post_id=test_post.id
        )
        async_session.add(like)
        await async_session.commit()
        like_id = like.id
        
        # 刪除用戶
        await async_session.delete(test_user)
        await async_session.commit()
        
        # 檢查按讚是否被刪除
        result = await async_session.get(Like, like_id)
        assert result is None
    
    async def test_cascade_delete_with_post(self, async_session, test_user, test_post):
        """測試文章刪除時，相關按讚也會被刪除"""
        like = Like(
            user_id=test_user.id,
            post_id=test_post.id
        )
        async_session.add(like)
        await async_session.commit()
        like_id = like.id
        
        # 刪除文章
        await async_session.delete(test_post)
        await async_session.commit()
        
        # 檢查按讚是否被刪除
        result = await async_session.get(Like, like_id)
        assert result is None
    
    async def test_multiple_users_can_like_same_post(self, async_session, test_post):
        """測試多個用戶可以按讚同一篇文章"""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # 創建第二個用戶
        user2 = User(
            email="user2@example.com",
            username="user2",
            hashed_password=get_password_hash("password")
        )
        async_session.add(user2)
        await async_session.commit()
        
        # 創建第三個用戶
        user3 = User(
            email="user3@example.com",
            username="user3",
            hashed_password=get_password_hash("password")
        )
        async_session.add(user3)
        await async_session.commit()
        
        # 三個用戶都按讚同一篇文章
        like1 = Like(user_id=user2.id, post_id=test_post.id)
        like2 = Like(user_id=user3.id, post_id=test_post.id)
        
        async_session.add_all([like1, like2])
        await async_session.commit()
        
        # 檢查按讚數量
        from sqlalchemy import select
        query = select(Like).where(Like.post_id == test_post.id)
        result = await async_session.execute(query)
        likes = result.scalars().all()
        
        assert len(likes) == 2