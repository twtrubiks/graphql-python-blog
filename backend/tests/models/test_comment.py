import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.comment import Comment
from app.models.post import Post


@pytest.mark.asyncio
class TestCommentModel:
    """Comment 模型測試"""

    async def test_create_comment_success(self, async_session, test_user, test_post):
        """測試成功創建評論"""
        comment = Comment(
            content="這是一個測試評論",
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add(comment)
        await async_session.commit()
        await async_session.refresh(comment)

        assert comment.id is not None
        assert comment.content == "這是一個測試評論"
        assert comment.user_id == test_user.id
        assert comment.post_id == test_post.id
        assert comment.created_at is not None
        assert comment.updated_at is not None

    async def test_comment_requires_content(self, async_session, test_user, test_post):
        """測試評論必須有內容"""
        comment = Comment(
            content=None,
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add(comment)
        with pytest.raises(IntegrityError):
            await async_session.commit()

    async def test_comment_requires_user(self, async_session, test_post):
        """測試評論必須有作者"""
        comment = Comment(
            content="測試評論",
            user_id=None,
            post_id=test_post.id
        )

        async_session.add(comment)
        with pytest.raises(IntegrityError):
            await async_session.commit()

    async def test_comment_requires_post(self, async_session, test_user):
        """測試評論必須關聯文章"""
        comment = Comment(
            content="測試評論",
            user_id=test_user.id,
            post_id=None
        )

        async_session.add(comment)
        with pytest.raises(IntegrityError):
            await async_session.commit()

    async def test_comment_relationships(self, async_session, test_user, test_post):
        """測試評論的關聯關係"""
        comment = Comment(
            content="測試評論",
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add(comment)
        await async_session.commit()
        await async_session.refresh(comment, ["author", "post"])

        assert comment.author.id == test_user.id
        assert comment.post.id == test_post.id

    async def test_cascade_delete_with_user(self, async_session, test_user, test_post):
        """測試刪除用戶時評論應該被級聯刪除"""
        comment = Comment(
            content="測試評論",
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add(comment)
        await async_session.commit()

        # 刪除用戶
        await async_session.delete(test_user)
        await async_session.commit()

        # 檢查評論是否被刪除
        result = await async_session.get(Comment, comment.id)
        assert result is None

    async def test_cascade_delete_with_post(self, async_session, test_user, test_post):
        """測試刪除文章時評論應該被級聯刪除"""
        comment = Comment(
            content="測試評論",
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add(comment)
        await async_session.commit()

        # 刪除文章
        await async_session.delete(test_post)
        await async_session.commit()

        # 檢查評論是否被刪除
        result = await async_session.get(Comment, comment.id)
        assert result is None

    async def test_comment_soft_delete(self, async_session, test_user, test_post):
        """測試評論軟刪除功能"""
        comment = Comment(
            content="測試評論",
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add(comment)
        await async_session.commit()

        # 軟刪除評論
        comment.deleted_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(comment)

        assert comment.deleted_at is not None
        assert comment.is_deleted is True

    async def test_multiple_comments_on_post(self, async_session, test_user, test_post):
        """測試一篇文章可以有多個評論"""
        comment1 = Comment(
            content="第一個評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        comment2 = Comment(
            content="第二個評論",
            user_id=test_user.id,
            post_id=test_post.id
        )

        async_session.add_all([comment1, comment2])
        await async_session.commit()

        # 從當前 session 重新載入 post
        result = await async_session.execute(
            select(Post).where(Post.id == test_post.id)
        )
        post = result.scalar_one()
        await async_session.refresh(post, ["comments"])

        assert len(post.comments) == 2
        assert any(c.content == "第一個評論" for c in post.comments)
        assert any(c.content == "第二個評論" for c in post.comments)