from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.comment import Comment
from app.models.post import Post, PostStatus


class CommentService:

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        post_id: int,
        content: str,
        user_id: int
    ) -> Comment:
        """創建新評論"""
        # 檢查內容是否為空
        if not content or not content.strip():
            raise ValueError("評論內容不能為空")

        # 檢查文章是否存在
        post = await db.get(Post, post_id)
        if not post:
            raise ValueError("文章不存在")

        # 檢查文章是否已發布（根據業務需求，可能允許作者評論草稿）
        if post.status != PostStatus.PUBLISHED:
            # 如果是作者本人，可以評論自己的草稿
            if post.author_id != user_id:
                raise ValueError("不能評論未發布的文章")

        # 創建評論
        comment = Comment(
            content=content.strip(),
            post_id=post_id,
            user_id=user_id
        )

        db.add(comment)
        await db.commit()
        await db.refresh(comment, ["author", "post"])

        return comment

    @staticmethod
    async def get_post_comments(
        db: AsyncSession,
        post_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Comment]:
        """獲取文章的評論列表"""
        query = select(Comment).where(
            and_(
                Comment.post_id == post_id,
                Comment.deleted_at.is_(None)  # 排除已刪除的評論
            )
        ).options(
            selectinload(Comment.author)
        ).order_by(Comment.created_at)  # 按創建時間排序

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_comment_count(db: AsyncSession, post_id: int) -> int:
        """獲取文章的評論總數"""
        query = select(Comment).where(
            and_(
                Comment.post_id == post_id,
                Comment.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        return len(result.scalars().all())

    @staticmethod
    async def update_comment(
        db: AsyncSession,
        comment_id: int,
        content: str,
        user_id: int
    ) -> Comment:
        """編輯評論 - 只有評論作者可以編輯"""
        # 檢查內容是否為空
        if not content or not content.strip():
            raise ValueError("評論內容不能為空")

        # 獲取評論
        comment = await db.get(Comment, comment_id, options=[selectinload(Comment.author), selectinload(Comment.post)])
        if not comment:
            raise ValueError("評論不存在")

        # 檢查是否已刪除
        if comment.deleted_at:
            raise ValueError("評論已被刪除")

        # 檢查權限：只有評論作者可以編輯（與刪除不同，文章作者不能編輯他人評論）
        if comment.user_id != user_id:
            raise PermissionError("沒有權限編輯此評論")

        # 更新內容
        comment.content = content.strip()
        comment.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(comment, ["author", "post"])

        return comment

    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        comment_id: int,
        user_id: int
    ) -> bool:
        """刪除評論（軟刪除）"""
        # 獲取評論
        comment = await db.get(Comment, comment_id, options=[selectinload(Comment.post)])
        if not comment:
            raise ValueError("評論不存在")

        # 檢查是否已刪除
        if comment.deleted_at:
            raise ValueError("評論已被刪除")

        # 檢查權限：評論作者或文章作者可以刪除
        if comment.user_id != user_id and comment.post.author_id != user_id:
            raise PermissionError("沒有權限刪除此評論")

        # 軟刪除
        comment.deleted_at = datetime.now(timezone.utc)
        await db.commit()

        return True

    @staticmethod
    async def get_comment_by_id(
        db: AsyncSession,
        comment_id: int
    ) -> Optional[Comment]:
        """根據ID獲取評論"""
        query = select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.deleted_at.is_(None)
            )
        ).options(
            selectinload(Comment.author),
            selectinload(Comment.post)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_comments(
        db: AsyncSession,
        user_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Comment]:
        """獲取用戶的所有評論"""
        query = select(Comment).where(
            and_(
                Comment.user_id == user_id,
                Comment.deleted_at.is_(None)
            )
        ).options(
            selectinload(Comment.post)
        ).order_by(Comment.created_at.desc())

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await db.execute(query)
        return result.scalars().all()