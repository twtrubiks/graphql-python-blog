"""測試 Tag 模型與多對多關聯"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tag import Tag, post_tags
from app.models.post import Post
from app.models.user import User


class TestTagModel:
    """測試 Tag 模型的基本功能"""
    
    @pytest.mark.asyncio
    async def test_create_tag(self, test_session: AsyncSession):
        """測試創建標籤"""
        # 創建標籤
        tag = Tag(name="python", slug="python")
        test_session.add(tag)
        await test_session.commit()
        await test_session.refresh(tag)
        
        # 驗證
        assert tag.id is not None
        assert tag.name == "python"
        assert tag.slug == "python"
        assert tag.created_at is not None
        assert tag.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_tag_unique_name(self, test_session: AsyncSession):
        """測試標籤名稱唯一性"""
        # 創建第一個標籤
        tag1 = Tag(name="python", slug="python")
        test_session.add(tag1)
        await test_session.commit()
        
        # 嘗試創建相同名稱的標籤
        tag2 = Tag(name="python", slug="python-2")
        test_session.add(tag2)
        
        with pytest.raises(Exception):  # 應該拋出唯一性約束異常
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_tag_unique_slug(self, test_session: AsyncSession):
        """測試標籤 slug 唯一性"""
        # 創建第一個標籤
        tag1 = Tag(name="Python", slug="python")
        test_session.add(tag1)
        await test_session.commit()
        
        # 嘗試創建相同 slug 的標籤
        tag2 = Tag(name="python 3", slug="python")
        test_session.add(tag2)
        
        with pytest.raises(Exception):  # 應該拋出唯一性約束異常
            await test_session.commit()


class TestPostTagRelationship:
    """測試 Post 和 Tag 的多對多關聯"""
    
    @pytest.mark.asyncio
    async def test_post_tag_association(self, test_session: AsyncSession):
        """測試文章和標籤的關聯"""
        # 創建用戶
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        test_session.add(user)
        await test_session.commit()
        
        # 創建文章
        post = Post(
            title="Test Post",
            slug="test-post",
            content="Test content",
            author_id=user.id
        )
        test_session.add(post)
        
        # 創建標籤
        tag1 = Tag(name="python", slug="python")
        tag2 = Tag(name="fastapi", slug="fastapi")
        test_session.add_all([tag1, tag2])
        
        await test_session.commit()
        
        # 使用 SQL 直接建立關聯
        await test_session.execute(
            post_tags.insert().values(post_id=post.id, tag_id=tag1.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post.id, tag_id=tag2.id)
        )
        await test_session.commit()
        
        # 重新載入以檢查關聯，使用 eager loading
        result = await test_session.execute(
            select(Post).options(selectinload(Post.tags)).where(Post.id == post.id)
        )
        post_refreshed = result.scalar_one()
        
        # 驗證關聯
        assert len(post_refreshed.tags) == 2
        tag_names = {tag.name for tag in post_refreshed.tags}
        assert "python" in tag_names
        assert "fastapi" in tag_names
    
    @pytest.mark.asyncio
    async def test_tag_posts_relationship(self, test_session: AsyncSession):
        """測試從標籤獲取相關文章"""
        # 創建用戶
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        test_session.add(user)
        await test_session.commit()
        
        # 創建標籤
        tag = Tag(name="python", slug="python")
        test_session.add(tag)
        
        # 創建多個文章
        post1 = Post(
            title="Python Tutorial",
            slug="python-tutorial",
            content="Content 1",
            author_id=user.id
        )
        post2 = Post(
            title="Python Tips",
            slug="python-tips",
            content="Content 2",
            author_id=user.id
        )
        test_session.add_all([post1, post2])
        await test_session.commit()
        
        # 使用 SQL 直接建立關聯
        await test_session.execute(
            post_tags.insert().values(post_id=post1.id, tag_id=tag.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post2.id, tag_id=tag.id)
        )
        await test_session.commit()
        
        # 重新載入以檢查關聯
        result = await test_session.execute(
            select(Tag).options(selectinload(Tag.posts)).where(Tag.id == tag.id)
        )
        tag_refreshed = result.scalar_one()
        
        # 驗證關聯
        assert len(tag_refreshed.posts) == 2
        post_titles = {post.title for post in tag_refreshed.posts}
        assert "Python Tutorial" in post_titles
        assert "Python Tips" in post_titles
    
    @pytest.mark.asyncio
    async def test_cascade_delete_post_tag_association(self, test_session: AsyncSession):
        """測試刪除文章時自動刪除關聯（但不刪除標籤）"""
        # 創建用戶
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        test_session.add(user)
        await test_session.commit()
        
        # 創建文章和標籤
        post = Post(
            title="Test Post",
            slug="test-post",
            content="Test content",
            author_id=user.id
        )
        tag = Tag(name="python", slug="python")
        test_session.add_all([post, tag])
        await test_session.commit()
        
        # 使用 SQL 直接建立關聯
        await test_session.execute(
            post_tags.insert().values(post_id=post.id, tag_id=tag.id)
        )
        await test_session.commit()
        
        # 刪除文章
        await test_session.delete(post)
        await test_session.commit()
        
        # 驗證標籤仍然存在
        result = await test_session.execute(
            select(Tag).where(Tag.id == tag.id)
        )
        existing_tag = result.scalar_one_or_none()
        assert existing_tag is not None
        assert existing_tag.name == "python"
    
    @pytest.mark.asyncio
    async def test_cascade_delete_tag_post_association(self, test_session: AsyncSession):
        """測試刪除標籤時自動刪除關聯（但不刪除文章）"""
        # 創建用戶
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        test_session.add(user)
        await test_session.commit()
        
        # 創建文章和標籤
        post = Post(
            title="Test Post",
            slug="test-post",
            content="Test content",
            author_id=user.id
        )
        tag = Tag(name="python", slug="python")
        test_session.add_all([post, tag])
        await test_session.commit()
        
        # 使用 SQL 直接建立關聯
        await test_session.execute(
            post_tags.insert().values(post_id=post.id, tag_id=tag.id)
        )
        await test_session.commit()
        
        # 刪除標籤
        await test_session.delete(tag)
        await test_session.commit()
        
        # 驗證文章仍然存在
        result = await test_session.execute(
            select(Post).where(Post.id == post.id)
        )
        existing_post = result.scalar_one_or_none()
        assert existing_post is not None
        assert existing_post.title == "Test Post"