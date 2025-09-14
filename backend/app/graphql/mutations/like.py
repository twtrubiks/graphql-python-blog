import strawberry
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user_id
from app.services.like import LikeService
from app.graphql.types.like import LikeMutationResponse


@strawberry.type
class LikeMutation:
    
    @strawberry.mutation
    async def like_post(
        self,
        post_id: strawberry.ID,
        info: strawberry.Info
    ) -> LikeMutationResponse:
        """按讚文章"""
        # 獲取當前用戶
        user_id = await get_current_user_id(info)
        if not user_id:
            raise Exception("需要登入才能按讚")
        
        # 獲取資料庫連接
        db: AsyncSession = info.context.get("db_session")
        
        try:
            # 執行按讚
            success, message = await LikeService.like_post(
                db=db,
                post_id=int(post_id),
                user_id=user_id
            )
            
            # 返回結果，不返回 post 以避免延遲載入問題
            return LikeMutationResponse(
                success=success,
                message=message,
                post=None  # 暫時不返回 post，避免 async 問題
            )
            
        except ValueError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"按讚失敗: {str(e)}")
    
    @strawberry.mutation
    async def unlike_post(
        self,
        post_id: strawberry.ID,
        info: strawberry.Info
    ) -> LikeMutationResponse:
        """取消按讚"""
        # 獲取當前用戶
        user_id = await get_current_user_id(info)
        if not user_id:
            raise Exception("需要登入才能取消按讚")
        
        # 獲取資料庫連接
        db: AsyncSession = info.context.get("db_session")
        
        try:
            # 執行取消按讚
            success, message = await LikeService.unlike_post(
                db=db,
                post_id=int(post_id),
                user_id=user_id
            )
            
            # 返回結果，不返回 post 以避免延遲載入問題
            return LikeMutationResponse(
                success=success,
                message=message,
                post=None  # 暫時不返回 post，避免 async 問題
            )
            
        except ValueError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"取消按讚失敗: {str(e)}")