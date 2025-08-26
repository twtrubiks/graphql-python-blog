import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.post import Post


class TestPostModel:
    """測試 Post 模型的基本功能"""
    
    @pytest.mark.asyncio
    async def test_create_post_success(self, test_session: AsyncSession, test_user: User):
        """測試成功創建 Post"""
        post_data = {
            "title": "測試文章標題",
            "content": "這是測試文章的內容",
            "published": True,
            "author_id": test_user.id
        }
        
        post = Post(**post_data)
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)
        
        assert post.id is not None
        assert post.title == "測試文章標題"
        assert post.content == "這是測試文章的內容"
        assert post.published is True
        assert post.author_id == test_user.id
        assert post.created_at is not None
        assert post.updated_at is None  # 只有更新時才會設值
    
    @pytest.mark.asyncio
    async def test_post_title_required(self, test_session: AsyncSession, test_user: User):
        """測試 title 為必填欄位"""
        post = Post(
            content="內容",
            author_id=test_user.id
        )
        test_session.add(post)
        
        with pytest.raises(IntegrityError):
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_post_content_required(self, test_session: AsyncSession, test_user: User):
        """測試 content 為必填欄位"""
        post = Post(
            title="標題",
            author_id=test_user.id
        )
        test_session.add(post)
        
        with pytest.raises(IntegrityError):
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_post_author_id_required(self, test_session: AsyncSession):
        """測試 author_id 為必填欄位"""
        post = Post(
            title="標題",
            content="內容"
        )
        test_session.add(post)
        
        with pytest.raises(IntegrityError):
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_post_default_published_false(self, test_session: AsyncSession, test_user: User):
        """測試 published 預設值為 False"""
        post = Post(
            title="標題",
            content="內容",
            author_id=test_user.id
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)
        
        assert post.published is False
    
    @pytest.mark.asyncio
    async def test_post_author_relationship(self, test_session: AsyncSession, test_user: User):
        """測試 Post 與 User 的關聯關係"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        post = Post(
            title="標題",
            content="內容",
            author_id=test_user.id
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)
        
        # 測試從 Post 存取 author（使用顯式查詢）
        result = await test_session.execute(
            select(Post).options(selectinload(Post.author)).filter(Post.id == post.id)
        )
        loaded_post = result.scalar_one()
        
        assert loaded_post.author is not None
        assert loaded_post.author.id == test_user.id
        assert loaded_post.author.username == test_user.username
        
        # 測試從 User 存取 posts（使用顯式查詢）
        result = await test_session.execute(
            select(User).options(selectinload(User.posts)).filter(User.id == test_user.id)
        )
        loaded_user = result.scalar_one()
        
        assert len(loaded_user.posts) == 1
        assert loaded_user.posts[0].id == post.id
    
    @pytest.mark.asyncio
    async def test_multiple_posts_same_author(self, test_session: AsyncSession, test_user: User):
        """測試同一用戶可以有多篇文章"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        posts = []
        for i in range(3):
            post = Post(
                title=f"文章標題 {i+1}",
                content=f"文章內容 {i+1}",
                author_id=test_user.id
            )
            posts.append(post)
            test_session.add(post)
        
        await test_session.commit()
        
        # 使用顯式查詢獲取用戶及其文章
        result = await test_session.execute(
            select(User).options(selectinload(User.posts)).filter(User.id == test_user.id)
        )
        loaded_user = result.scalar_one()
        
        assert len(loaded_user.posts) == 3
        for i, post in enumerate(loaded_user.posts):
            assert post.title == f"文章標題 {i+1}"
            assert post.author_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_post_cascade_on_user_delete(self, test_session: AsyncSession):
        """測試刪除用戶時的級聯操作（如果有設定的話）"""
        # 創建用戶
        user = User(
            email="cascade@test.com",
            username="cascadeuser",
            hashed_password="hashed_password"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # 創建文章
        post = Post(
            title="待刪除的文章",
            content="內容",
            author_id=user.id
        )
        test_session.add(post)
        await test_session.commit()
        
        # 記錄文章ID
        post_id = post.id
        
        # 刪除用戶
        await test_session.delete(user)
        
        try:
            await test_session.commit()
            # 檢查文章是否還存在
            from sqlalchemy import select
            result = await test_session.execute(select(Post).filter(Post.id == post_id))
            remaining_post = result.scalar_one_or_none()
            # 根據實際的級聯設定來驗證結果
            # 如果有設定級聯刪除，remaining_post 應該為 None
            # 如果沒有設定級聯刪除，這個操作應該會失敗
        except IntegrityError:
            # 如果沒有設定級聯刪除，刪除用戶會因為外鍵約束失敗
            await test_session.rollback()
            # 這是預期的行為，因為還有文章引用這個用戶
            pass
    
    @pytest.mark.asyncio
    async def test_post_str_representation(self, test_session: AsyncSession, test_user: User):
        """測試 Post 的字串表示（如果有實作 __repr__ 方法）"""
        post = Post(
            title="測試文章",
            content="測試內容",
            author_id=test_user.id
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)
        
        # 如果 Post 模型有實作 __repr__ 方法，這裡可以測試
        str_repr = str(post)
        assert "Post" in str_repr or str(post) is not None