import strawberry
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user_id
from app.services.comment import CommentService
from app.graphql.types.comment import Comment as CommentType, CommentMutationResponse, UpdateCommentInput
from app.graphql.utils import convert_model_to_graphql
from app.graphql.subscriptions.comment import (
    CommentEvent,
    CommentUpdatedEvent,
    CommentDeletedEvent,
    CommentDeletedPayload,
)


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
            
            # 發送即時通知給訂閱者
            await CommentEvent.publish(str(post_id), comment_type)
            
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
            # 刪除評論（軟刪除）
            comment = await CommentService.delete_comment(
                db=db,
                comment_id=int(comment_id),
                user_id=user_id
            )

            # 發送即時通知給訂閱者；留言數由伺服器計算絕對值，避免前端各自 -1 造成不同步
            total_comments = await CommentService.get_comment_count(db, comment.post_id)
            await CommentDeletedEvent.publish(
                str(comment.post_id),
                CommentDeletedPayload(
                    comment_id=str(comment.id),
                    post_id=str(comment.post_id),
                    total_comments=total_comments,
                ),
            )

            return CommentMutationResponse(
                success=True,
                message="評論已成功刪除"
            )
            
        except ValueError as e:
            raise Exception(str(e))
        except PermissionError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"刪除評論失敗: {str(e)}")

    @strawberry.mutation
    async def update_comment(
        self,
        comment_id: strawberry.ID,
        input: UpdateCommentInput,
        info: strawberry.Info
    ) -> CommentMutationResponse:
        """編輯評論 - 只有評論作者可以編輯"""
        # 獲取當前用戶
        user_id = await get_current_user_id(info)
        if not user_id:
            raise Exception("需要登入才能編輯評論")

        # 獲取資料庫連接
        db: AsyncSession = info.context.get("db_session")

        try:
            # 編輯評論
            comment = await CommentService.update_comment(
                db=db,
                comment_id=int(comment_id),
                content=input.content,
                user_id=user_id
            )

            # 轉換為 GraphQL type
            comment_type = convert_model_to_graphql(comment, CommentType)
            comment_type.author = comment.author
            comment_type.post = comment.post

            # 發送即時通知給訂閱者
            await CommentUpdatedEvent.publish(str(comment.post_id), comment_type)

            return CommentMutationResponse(
                success=True,
                message="評論已成功編輯",
                comment=comment_type
            )

        except ValueError as e:
            raise Exception(str(e))
        except PermissionError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"編輯評論失敗: {str(e)}")