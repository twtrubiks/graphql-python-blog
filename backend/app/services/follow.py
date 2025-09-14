"""追蹤功能服務層"""
from typing import Optional
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.follow import Follow


class FollowService:
    """追蹤功能服務"""
    
    @staticmethod
    async def follow_user(
        session: AsyncSession,
        follower_id: int,
        followed_id: int
    ) -> tuple[bool, str, Optional[Follow]]:
        """
        追蹤用戶
        
        Returns:
            tuple: (success, message, follow_object)
        """
        # 檢查是否追蹤自己
        if follower_id == followed_id:
            return False, "Cannot follow yourself", None
        
        # 檢查被追蹤用戶是否存在
        result = await session.execute(
            select(User).where(User.id == followed_id)
        )
        followed_user = result.scalar_one_or_none()
        
        if not followed_user:
            return False, "User not found", None
        
        # 檢查是否已經追蹤
        result = await session.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == follower_id,
                    Follow.followed_id == followed_id
                )
            )
        )
        existing_follow = result.scalar_one_or_none()
        
        if existing_follow:
            return False, "Already following this user", None
        
        # 創建追蹤關係
        try:
            follow = Follow(
                follower_id=follower_id,
                followed_id=followed_id
            )
            session.add(follow)
            await session.commit()
            await session.refresh(follow)
            
            # 載入關聯物件
            result = await session.execute(
                select(Follow)
                .where(Follow.id == follow.id)
                .options(
                    selectinload(Follow.follower),
                    selectinload(Follow.followed)
                )
            )
            follow = result.scalar_one()
            
            return True, "Successfully followed user", follow
        except IntegrityError:
            await session.rollback()
            return False, "Failed to follow user", None
    
    @staticmethod
    async def unfollow_user(
        session: AsyncSession,
        follower_id: int,
        followed_id: int
    ) -> tuple[bool, str]:
        """
        取消追蹤用戶
        
        Returns:
            tuple: (success, message)
        """
        # 查找追蹤關係
        result = await session.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == follower_id,
                    Follow.followed_id == followed_id
                )
            )
        )
        follow = result.scalar_one_or_none()
        
        if not follow:
            return False, "Not following this user"
        
        # 刪除追蹤關係
        await session.delete(follow)
        await session.commit()
        
        return True, "Successfully unfollowed user"
    
    @staticmethod
    async def is_following(
        session: AsyncSession,
        follower_id: int,
        followed_id: int
    ) -> bool:
        """檢查是否正在追蹤某用戶"""
        result = await session.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == follower_id,
                    Follow.followed_id == followed_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def get_followers_count(session: AsyncSession, user_id: int) -> int:
        """獲取追蹤者數量"""
        result = await session.execute(
            select(func.count(Follow.id)).where(Follow.followed_id == user_id)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def get_following_count(session: AsyncSession, user_id: int) -> int:
        """獲取追蹤中數量"""
        result = await session.execute(
            select(func.count(Follow.id)).where(Follow.follower_id == user_id)
        )
        return result.scalar() or 0