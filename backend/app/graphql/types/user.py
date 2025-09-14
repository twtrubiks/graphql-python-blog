import strawberry
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info

from app.models.follow import Follow
from app.services.follow import FollowService
from app.core.deps import get_current_user_id


@strawberry.type
class UserType:
    id: strawberry.ID
    email: str
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @strawberry.field
    async def followers_count(self, info: Info) -> int:
        """獲取追蹤者數量"""
        session: AsyncSession = info.context.get("db_session")
        return await FollowService.get_followers_count(session, int(self.id))
    
    @strawberry.field
    async def following_count(self, info: Info) -> int:
        """獲取追蹤中數量"""
        session: AsyncSession = info.context.get("db_session")
        return await FollowService.get_following_count(session, int(self.id))
    
    @strawberry.field
    async def followers(self, info: Info) -> List["UserType"]:
        """獲取追蹤者列表"""
        session: AsyncSession = info.context.get("db_session")
        
        result = await session.execute(
            select(Follow)
            .where(Follow.followed_id == int(self.id))
            .options(selectinload(Follow.follower))
        )
        follows = result.scalars().all()
        
        return [UserType.from_orm(f.follower) for f in follows]
    
    @strawberry.field
    async def following(self, info: Info) -> List["UserType"]:
        """獲取追蹤中列表"""
        session: AsyncSession = info.context.get("db_session")
        
        result = await session.execute(
            select(Follow)
            .where(Follow.follower_id == int(self.id))
            .options(selectinload(Follow.followed))
        )
        follows = result.scalars().all()
        
        return [UserType.from_orm(f.followed) for f in follows]
    
    @strawberry.field
    async def is_followed_by_me(self, info: Info) -> bool:
        """檢查當前用戶是否追蹤此用戶"""
        current_user_id = await get_current_user_id(info)
        if not current_user_id:
            return False
        
        session: AsyncSession = info.context.get("db_session")
        return await FollowService.is_following(session, current_user_id, int(self.id))
    
    @classmethod
    def from_orm(cls, user):
        """從 SQLAlchemy 模型創建 UserType"""
        return cls(
            id=strawberry.ID(str(user.id)),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )