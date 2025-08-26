from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.post import Post, PostStatus
from slugify import slugify


class PostService:
    @staticmethod
    async def _ensure_unique_slug(session: AsyncSession, base_slug: str) -> str:
        """Ensure slug is unique by querying all similar slugs at once"""
        # Query all slugs that match the pattern
        stmt = select(Post.slug).where(
            Post.slug.like(f"{base_slug}%")
        )
        result = await session.execute(stmt)
        existing_slugs = {row[0] for row in result}
        
        # If base slug doesn't exist, use it
        if base_slug not in existing_slugs:
            return base_slug
        
        # Find the next available number
        counter = 1
        while f"{base_slug}-{counter}" in existing_slugs:
            counter += 1
        
        return f"{base_slug}-{counter}"
    
    @staticmethod
    async def create_post(
        session: AsyncSession,
        title: str,
        content: str,
        author_id: int,
        excerpt: Optional[str] = None,
        slug: Optional[str] = None,
        status: PostStatus = PostStatus.DRAFT
    ) -> Post:
        """Create a new post"""
        
        # Generate slug if not provided
        if not slug:
            base_slug = slugify(title)
        else:
            base_slug = slugify(slug)
        
        # Ensure slug is unique with optimized query
        slug = await PostService._ensure_unique_slug(session, base_slug)
        
        # Create the post
        post = Post(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            status=status,
            author_id=author_id
        )
        
        # Set published_at if status is published
        if status == PostStatus.PUBLISHED:
            post.published_at = datetime.now(timezone.utc)
        
        session.add(post)
        await session.commit()
        await session.refresh(post)
        
        return post
    
    @staticmethod
    async def get_post_by_id(session: AsyncSession, post_id: int) -> Optional[Post]:
        """Get a post by ID"""
        stmt = select(Post).where(Post.id == post_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_post_by_slug(session: AsyncSession, slug: str) -> Optional[Post]:
        """Get a post by slug"""
        stmt = select(Post).where(Post.slug == slug)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()