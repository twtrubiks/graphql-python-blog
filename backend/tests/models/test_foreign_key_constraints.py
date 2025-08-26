import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.post import Post


class TestForeignKeyConstraints:
    """測試外鍵約束設置"""
    
    @pytest.mark.asyncio
    async def test_post_author_foreign_key_exists(self, test_session: AsyncSession):
        """測試 Post.author_id 外鍵約束是否正確設置"""
        # 檢查資料庫中的外鍵約束
        result = await test_session.execute(text("""
            SELECT 
                tc.constraint_name, 
                tc.table_name, 
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE 
                tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = 'posts'
                AND kcu.column_name = 'author_id';
        """))
        
        constraints = result.fetchall()
        assert len(constraints) > 0, "應該有 posts.author_id 的外鍵約束"
        
        constraint = constraints[0]
        assert constraint.foreign_table_name == 'users'
        assert constraint.foreign_column_name == 'id'
    
    @pytest.mark.asyncio
    async def test_valid_foreign_key_relationship(self, test_session: AsyncSession):
        """測試有效的外鍵關聯"""
        # 創建用戶
        user = User(
            email="valid@test.com",
            username="validuser",
            hashed_password="hash123"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # 創建引用有效用戶ID的文章
        post = Post(
            title="有效文章",
            content="文章內容",
            author_id=user.id  # 有效的外鍵
        )
        test_session.add(post)
        
        # 應該成功提交
        await test_session.commit()
        await test_session.refresh(post)
        
        assert post.id is not None
        assert post.author_id == user.id
    
    @pytest.mark.asyncio
    async def test_invalid_foreign_key_constraint_violation(self, test_session: AsyncSession):
        """測試無效外鍵約束違規"""
        # 嘗試創建引用不存在用戶ID的文章
        post = Post(
            title="無效文章",
            content="文章內容", 
            author_id=99999  # 不存在的用戶ID
        )
        test_session.add(post)
        
        # 應該因為外鍵約束失敗
        with pytest.raises((IntegrityError, Exception)) as exc_info:
            await test_session.commit()
        
        # 驗證是外鍵約束錯誤
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['foreign', 'key', 'constraint', 'violates'])
    
    @pytest.mark.asyncio
    async def test_null_foreign_key_constraint(self, test_session: AsyncSession):
        """測試空外鍵約束"""
        # 嘗試創建 author_id 為 NULL 的文章
        post = Post(
            title="無作者文章",
            content="文章內容"
            # author_id 沒有設置，將是 NULL
        )
        test_session.add(post)
        
        # 應該因為 NOT NULL 約束失敗
        with pytest.raises((IntegrityError, Exception)) as exc_info:
            await test_session.commit()
        
        # 驗證是 NOT NULL 約束錯誤
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['null', 'not null', 'violates'])
    
    @pytest.mark.asyncio
    async def test_cascade_delete_enforcement(self, test_session: AsyncSession):
        """測試級聯刪除約束執行"""
        # 創建用戶和文章
        user = User(
            email="cascade@test.com",
            username="cascadeuser",
            hashed_password="hash123"
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
        
        # 記錄文章ID
        post_ids = [post.id for post in posts]
        
        # 刪除用戶（應該觸發級聯刪除）
        await test_session.delete(user)
        await test_session.commit()
        
        # 驗證所有關聯文章都被刪除
        from sqlalchemy import select
        for post_id in post_ids:
            result = await test_session.execute(select(Post).filter(Post.id == post_id))
            deleted_post = result.scalar_one_or_none()
            assert deleted_post is None, f"Post with id {post_id} 應該被級聯刪除"
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraint_on_update(self, test_session: AsyncSession):
        """測試更新時的外鍵約束"""
        # 創建兩個用戶
        user1 = User(email="user1@test.com", username="user1", hashed_password="hash1")
        user2 = User(email="user2@test.com", username="user2", hashed_password="hash2")
        test_session.add_all([user1, user2])
        await test_session.commit()
        await test_session.refresh(user1)
        await test_session.refresh(user2)
        
        # 創建屬於用戶1的文章
        post = Post(
            title="測試文章",
            content="測試內容",
            author_id=user1.id
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)
        
        # 更新文章的作者為用戶2（有效更新）
        post.author_id = user2.id
        await test_session.commit()
        
        assert post.author_id == user2.id
        
        # 嘗試更新為不存在的用戶ID（應該失敗）
        post.author_id = 99999
        with pytest.raises((IntegrityError, Exception)):
            await test_session.commit()