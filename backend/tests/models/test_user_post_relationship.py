import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.post import Post


class TestUserPostRelationship:
    """測試 User 和 Post 之間的關聯關係"""
    
    @pytest.mark.asyncio
    async def test_user_create_posts(self, test_session: AsyncSession, test_user: User):
        """測試用戶創建多篇文章"""
        # 創建多篇文章
        posts_data = [
            {"title": "第一篇文章", "content": "第一篇內容", "published": True},
            {"title": "第二篇文章", "content": "第二篇內容", "published": False},
            {"title": "第三篇文章", "content": "第三篇內容", "published": True},
        ]
        
        created_posts = []
        for post_data in posts_data:
            post = Post(**post_data, author_id=test_user.id)
            created_posts.append(post)
            test_session.add(post)
        
        await test_session.commit()
        
        # 驗證關聯關係
        result = await test_session.execute(
            select(User).options(selectinload(User.posts)).filter(User.id == test_user.id)
        )
        loaded_user = result.scalar_one()
        
        assert len(loaded_user.posts) == 3
        
        # 驗證每篇文章的作者都是正確的
        for post in loaded_user.posts:
            assert post.author_id == test_user.id
            result = await test_session.execute(
                select(Post).options(selectinload(Post.author)).filter(Post.id == post.id)
            )
            loaded_post = result.scalar_one()
            assert loaded_post.author.id == test_user.id
            assert loaded_post.author.username == test_user.username
    
    @pytest.mark.asyncio
    async def test_post_belongs_to_user(self, test_session: AsyncSession):
        """測試文章屬於特定用戶"""
        # 創建兩個用戶
        user1 = User(
            email="user1@test.com",
            username="user1",
            hashed_password="hash1"
        )
        user2 = User(
            email="user2@test.com", 
            username="user2",
            hashed_password="hash2"
        )
        test_session.add_all([user1, user2])
        await test_session.commit()
        await test_session.refresh(user1)
        await test_session.refresh(user2)
        
        # 為每個用戶創建文章
        post1 = Post(title="用戶1的文章", content="內容1", author_id=user1.id)
        post2 = Post(title="用戶2的文章", content="內容2", author_id=user2.id)
        test_session.add_all([post1, post2])
        await test_session.commit()
        
        # 驗證文章歸屬
        result = await test_session.execute(
            select(Post).options(selectinload(Post.author)).filter(Post.id == post1.id)
        )
        loaded_post1 = result.scalar_one()
        
        result = await test_session.execute(
            select(Post).options(selectinload(Post.author)).filter(Post.id == post2.id)
        )
        loaded_post2 = result.scalar_one()
        
        assert loaded_post1.author.id == user1.id
        assert loaded_post1.author.username == "user1"
        assert loaded_post2.author.id == user2.id  
        assert loaded_post2.author.username == "user2"
    
    @pytest.mark.asyncio
    async def test_cascade_delete_posts_when_user_deleted(self, test_session: AsyncSession):
        """測試刪除用戶時級聯刪除文章"""
        # 創建用戶和文章
        user = User(
            email="cascade@test.com",
            username="cascadeuser", 
            hashed_password="hash"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # 創建多篇文章
        posts = []
        for i in range(3):
            post = Post(
                title=f"文章 {i+1}",
                content=f"內容 {i+1}",
                author_id=user.id
            )
            posts.append(post)
            test_session.add(post)
        
        await test_session.commit()
        post_ids = [post.id for post in posts]
        
        # 刪除用戶
        await test_session.delete(user)
        await test_session.commit()
        
        # 驗證文章是否被級聯刪除
        for post_id in post_ids:
            result = await test_session.execute(select(Post).filter(Post.id == post_id))
            deleted_post = result.scalar_one_or_none()
            assert deleted_post is None, f"Post with id {post_id} should be deleted"
    
    @pytest.mark.asyncio
    async def test_filter_posts_by_published_status(self, test_session: AsyncSession, test_user: User):
        """測試根據發布狀態篩選文章"""
        # 創建已發布和未發布的文章
        posts_data = [
            {"title": "已發布文章1", "content": "內容1", "published": True},
            {"title": "已發布文章2", "content": "內容2", "published": True},
            {"title": "草稿文章1", "content": "內容3", "published": False},
            {"title": "草稿文章2", "content": "內容4", "published": False},
        ]
        
        for post_data in posts_data:
            post = Post(**post_data, author_id=test_user.id)
            test_session.add(post)
        
        await test_session.commit()
        
        # 查詢已發布的文章
        result = await test_session.execute(
            select(Post)
            .filter(Post.author_id == test_user.id)
            .filter(Post.published == True)
        )
        published_posts = result.scalars().all()
        
        # 查詢草稿文章
        result = await test_session.execute(
            select(Post)
            .filter(Post.author_id == test_user.id) 
            .filter(Post.published == False)
        )
        draft_posts = result.scalars().all()
        
        assert len(published_posts) == 2
        assert len(draft_posts) == 2
        
        for post in published_posts:
            assert post.published is True
            assert "已發布" in post.title
            
        for post in draft_posts:
            assert post.published is False
            assert "草稿" in post.title
    
    @pytest.mark.asyncio
    async def test_user_post_count(self, test_session: AsyncSession):
        """測試統計用戶文章數量"""
        # 創建兩個用戶
        user1 = User(email="user1@test.com", username="user1", hashed_password="hash1")
        user2 = User(email="user2@test.com", username="user2", hashed_password="hash2")
        test_session.add_all([user1, user2])
        await test_session.commit()
        await test_session.refresh(user1)
        await test_session.refresh(user2)
        
        # 為用戶1創建5篇文章
        for i in range(5):
            post = Post(title=f"用戶1文章{i+1}", content=f"內容{i+1}", author_id=user1.id)
            test_session.add(post)
        
        # 為用戶2創建3篇文章
        for i in range(3):
            post = Post(title=f"用戶2文章{i+1}", content=f"內容{i+1}", author_id=user2.id)
            test_session.add(post)
        
        await test_session.commit()
        
        # 統計文章數量
        from sqlalchemy import func
        
        # 統計用戶1的文章數量
        result = await test_session.execute(
            select(func.count(Post.id)).filter(Post.author_id == user1.id)
        )
        user1_post_count = result.scalar()
        
        # 統計用戶2的文章數量
        result = await test_session.execute(
            select(func.count(Post.id)).filter(Post.author_id == user2.id)
        )
        user2_post_count = result.scalar()
        
        assert user1_post_count == 5
        assert user2_post_count == 3
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, test_session: AsyncSession):
        """測試外鍵約束"""
        # 嘗試創建指向不存在用戶的文章
        post = Post(
            title="無效文章",
            content="內容",
            author_id=99999  # 不存在的用戶ID
        )
        test_session.add(post)
        
        # 應該因為外鍵約束而失敗
        with pytest.raises(Exception):  # 可能是 IntegrityError 或其他異常
            await test_session.commit()