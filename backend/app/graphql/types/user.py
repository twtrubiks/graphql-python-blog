import strawberry
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info
from strawberry.permission import PermissionExtension

from app.models.follow import Follow
from app.services.follow import FollowService
from app.graphql.dataloaders import FOLLOW_LIST_LIMIT
from app.graphql.permissions import IsOwnerOrSuperuser


@strawberry.type
class UserType:
    id: strawberry.ID
    email: Optional[str] = strawberry.field(
        extensions=[PermissionExtension(permissions=[IsOwnerOrSuperuser()], fail_silently=True)]
    )
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
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            return await dataloaders.get_followers_count_loader().load(int(self.id))
        
        # Fallback to direct database query
        session: AsyncSession = info.context.get("db_session")
        return await FollowService.get_followers_count(session, int(self.id))
    
    @strawberry.field
    async def following_count(self, info: Info) -> int:
        """獲取追蹤中數量"""
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            return await dataloaders.get_following_count_loader().load(int(self.id))
        
        # Fallback to direct database query
        session: AsyncSession = info.context.get("db_session")
        return await FollowService.get_following_count(session, int(self.id))
    
    @strawberry.field
    async def followers(self, info: Info) -> List["UserType"]:
        """獲取追蹤者列表（最多 FOLLOW_LIST_LIMIT 個）"""
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            users = await dataloaders.get_followers_loader().load(int(self.id))
            return [UserType.from_orm(user) for user in users]

        # Fallback to direct database query
        session: AsyncSession = info.context.get("db_session")
        result = await session.execute(
            select(Follow)
            .where(Follow.followed_id == int(self.id))
            .options(selectinload(Follow.follower))
            .order_by(Follow.created_at.desc(), Follow.id.desc())
            .limit(FOLLOW_LIST_LIMIT)
        )
        follows = result.scalars().all()

        return [UserType.from_orm(f.follower) for f in follows]

    @strawberry.field
    async def following(self, info: Info) -> List["UserType"]:
        """獲取追蹤中列表（最多 FOLLOW_LIST_LIMIT 個）"""
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            users = await dataloaders.get_following_loader().load(int(self.id))
            return [UserType.from_orm(user) for user in users]

        # Fallback to direct database query
        session: AsyncSession = info.context.get("db_session")
        result = await session.execute(
            select(Follow)
            .where(Follow.follower_id == int(self.id))
            .options(selectinload(Follow.followed))
            .order_by(Follow.created_at.desc(), Follow.id.desc())
            .limit(FOLLOW_LIST_LIMIT)
        )
        follows = result.scalars().all()

        return [UserType.from_orm(f.followed) for f in follows]

    @strawberry.field
    async def is_followed_by_me(self, info: Info) -> bool:
        """檢查當前用戶是否追蹤此用戶"""
        # context.user_id 由 JWT 解碼並快取，不會每個欄位重查資料庫
        current_user_id = info.context.get("user_id")
        if not current_user_id:
            return False

        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            return await dataloaders.get_is_followed_loader().load(int(self.id))

        # Fallback to direct database query
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