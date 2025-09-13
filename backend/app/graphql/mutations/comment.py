import strawberry
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user_id
from app.core.database import get_async_session
from app.services.comment import CommentService
from app.graphql.types.comment import Comment as CommentType, CommentMutationResponse
from app.graphql.utils import convert_model_to_graphql


@strawberry.type
class CommentMutation:
    
    @strawberry.mutation
    async def add_comment(
        self,
        post_id: strawberry.ID,
        content: str,
        info: strawberry.Info
    ) -> CommentType:
        """新增評論到文章"""
        # 獲取當前用戶
        user_id = await get_current_user_id(info)
        if not user_id:
            raise Exception("需要登入才能評論")
        
        # 獲取資料庫連接
        db: AsyncSession = info.context.get("db_session")
        
        try:
            # 創建評論
            comment = await CommentService.create_comment(
                db=db,
                post_id=int(post_id),
                content=content,
                user_id=user_id
            )
            
            # 轉換為 GraphQL type
            comment_type = convert_model_to_graphql(comment, CommentType)
            # Add relationships
            comment_type.author = comment.author
            comment_type.post = comment.post
            return comment_type
            
        except ValueError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"創建評論失敗: {str(e)}")
    
    @strawberry.mutation
    async def delete_comment(
        self,
        comment_id: strawberry.ID,
        info: strawberry.Info
    ) -> CommentMutationResponse:
        """刪除評論"""
        # 獲取當前用戶
        user_id = await get_current_user_id(info)
        if not user_id:
            raise Exception("需要登入才能刪除評論")
        
        # 獲取資料庫連接
        db: AsyncSession = info.context.get("db_session")
        
        try:
            # 刪除評論
            success = await CommentService.delete_comment(
                db=db,
                comment_id=int(comment_id),
                user_id=user_id
            )
            
            return CommentMutationResponse(
                success=success,
                message="評論已成功刪除" if success else "刪除失敗"
            )
            
        except ValueError as e:
            raise Exception(str(e))
        except PermissionError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"刪除評論失敗: {str(e)}")