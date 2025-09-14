from typing import Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.like import Like
from app.models.post import Post


class LikeService:
    
    @staticmethod
    async def like_post(
        db: AsyncSession,
        post_id: int,
        user_id: int
    ) -> tuple[bool, str]:
        """
        按讚文章
        返回 (成功狀態, 訊息)
        """
        # 檢查文章是否存在
        post = await db.get(Post, post_id)
        if not post:
            raise ValueError("文章不存在")
        
        # 檢查是否已經按讚
        existing_like = await db.execute(
            select(Like).where(
                and_(
                    Like.user_id == user_id,
                    Like.post_id == post_id
                )
            )
        )
        if existing_like.scalar_one_or_none():
            return False, "您已經按讚過這篇文章"
        
        # 創建按讚
        try:
            like = Like(
                user_id=user_id,
                post_id=post_id
            )
            db.add(like)
            await db.commit()
            return True, "按讚成功"
        except IntegrityError:
            await db.rollback()
            return False, "您已經按讚過這篇文章"
    
    @staticmethod
    async def unlike_post(
        db: AsyncSession,
        post_id: int,
        user_id: int
    ) -> tuple[bool, str]:
        """
        取消按讚
        返回 (成功狀態, 訊息)
        """
        # 檢查文章是否存在
        post = await db.get(Post, post_id)
        if not post:
            raise ValueError("文章不存在")
        
        # 查找按讚記錄
        result = await db.execute(
            select(Like).where(
                and_(
                    Like.user_id == user_id,
                    Like.post_id == post_id
                )
            )
        )
        like = result.scalar_one_or_none()
        
        if not like:
            return False, "您沒有按讚過這篇文章"
        
        # 刪除按讚
        await db.delete(like)
        await db.commit()
        return True, "取消按讚成功"
    
    @staticmethod
    async def get_post_likes_count(
        db: AsyncSession,
        post_id: int
    ) -> int:
        """獲取文章的按讚數"""
        result = await db.execute(
            select(func.count(Like.id)).where(Like.post_id == post_id)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def is_post_liked_by_user(
        db: AsyncSession,
        post_id: int,
        user_id: Optional[int]
    ) -> bool:
        """檢查用戶是否按讚了文章"""
        if not user_id:
            return False
        
        result = await db.execute(
            select(Like).where(
                and_(
                    Like.user_id == user_id,
                    Like.post_id == post_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def get_user_liked_posts(
        db: AsyncSession,
        user_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> list[int]:
        """獲取用戶按讚的文章ID列表"""
        query = select(Like.post_id).where(Like.user_id == user_id)
        
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        result = await db.execute(query)
        return [row[0] for row in result]