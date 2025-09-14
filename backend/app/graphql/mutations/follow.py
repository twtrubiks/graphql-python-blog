"""追蹤功能 GraphQL mutations"""
import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id
from app.services.follow import FollowService
from app.graphql.types.follow import FollowType, FollowResponse, UnfollowResponse
from app.graphql.types.user import UserType


@strawberry.type
class FollowMutation:
    """追蹤功能 mutations"""
    
    @strawberry.mutation
    async def follow_user(
        self,
        user_id: strawberry.ID,
        info: strawberry.Info
    ) -> FollowResponse:
        """追蹤用戶"""
        # 獲取當前用戶
        current_user_id = await get_current_user_id(info)
        if not current_user_id:
            return FollowResponse(success=False, message="Authentication required", follow=None)
        
        # 獲取資料庫連接
        session: AsyncSession = info.context.get("db_session")
        
        success, message, follow = await FollowService.follow_user(
            session=session,
            follower_id=current_user_id,
            followed_id=int(user_id)
        )
        
        if follow:
            # 轉換為 GraphQL 類型
            follow_type = FollowType(
                id=strawberry.ID(str(follow.id)),
                follower=UserType.from_orm(follow.follower),
                followed=UserType.from_orm(follow.followed),
                created_at=follow.created_at
            )
            return FollowResponse(success=True, message=message, follow=follow_type)
        
        return FollowResponse(success=False, message=message, follow=None)
    
    @strawberry.mutation
    async def unfollow_user(
        self,
        user_id: strawberry.ID,
        info: strawberry.Info
    ) -> UnfollowResponse:
        """取消追蹤用戶"""
        # 獲取當前用戶
        current_user_id = await get_current_user_id(info)
        if not current_user_id:
            return UnfollowResponse(success=False, message="Authentication required")
        
        # 獲取資料庫連接
        session: AsyncSession = info.context.get("db_session")
        
        success, message = await FollowService.unfollow_user(
            session=session,
            follower_id=current_user_id,
            followed_id=int(user_id)
        )
        
        return UnfollowResponse(success=success, message=message)