"""測試資料工廠

提供簡化的測試資料建立方法
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.post import Post, PostStatus
from app.core.security import get_password_hash
from slugify import slugify


class UserFactory:
    """用戶資料工廠"""
    
    _counter = 0
    
    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password: str = "password123",
        is_active: bool = True,
        is_superuser: bool = False,
        bio: Optional[str] = None
    ) -> User:
        """建立測試用戶"""
        cls._counter += 1
        
        if not email:
            email = f"user{cls._counter}@example.com"
        if not username:
            username = f"user{cls._counter}"
        
        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            is_active=is_active,
            is_superuser=is_superuser,
            bio=bio or f"I am {username}"
        )
        
        session.add(user)
        await session.flush()
        return user


class PostFactory:
    """文章資料工廠"""
    
    _counter = 0
    
    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        author_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        status: PostStatus = PostStatus.PUBLISHED,
        slug: Optional[str] = None,
        excerpt: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Post:
        """建立測試文章"""
        cls._counter += 1
        
        if not title:
            title = f"Test Post {cls._counter}"
        
        if not content:
            content = f"This is the content for {title}"
        
        if not slug:
            slug = slugify(title)
        
        post = Post(
            title=title,
            content=content,
            slug=slug,
            excerpt=excerpt,
            status=status,
            author_id=author_id,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc)
        )
        
        session.add(post)
        await session.flush()
        return post