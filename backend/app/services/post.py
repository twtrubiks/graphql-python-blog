from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from sqlalchemy.orm import joinedload, selectinload
from app.models.post import Post, PostStatus
from app.models.tag import Tag, post_tags
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
        
        # Reload with relationships to avoid lazy loading issues
        result = await session.execute(
            select(Post)
            .options(
                selectinload(Post.tags),
                joinedload(Post.author)
            )
            .where(Post.id == post.id)
        )
        return result.scalar_one()
    
    @staticmethod
    async def get_post_by_id(
        session: AsyncSession, 
        post_id: int,
        include_tags: bool = False
    ) -> Optional[Post]:
        """Get a post by ID (excludes soft-deleted posts)"""
        stmt = select(Post).where(
            Post.id == post_id,
            Post.deleted_at.is_(None)  # Exclude soft-deleted posts
        )
        
        # Optionally include tags
        if include_tags:
            stmt = stmt.options(selectinload(Post.tags))
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_post_by_slug(
        session: AsyncSession,
        slug: str,
        current_user_id: Optional[int] = None
    ) -> Optional[Post]:
        """Get a post by slug with permission check

        - Published posts are visible to everyone
        - Draft/archived posts are only visible to their authors
        - Soft-deleted posts are not visible
        """
        stmt = select(Post).options(
            joinedload(Post.author),
            selectinload(Post.tags)
        ).where(
            Post.slug == slug,
            Post.deleted_at.is_(None)  # Exclude soft-deleted posts
        )
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()

        if not post:
            return None

        # Check permissions
        if post.status == PostStatus.PUBLISHED:
            return post

        # Draft or archived posts - only visible to author
        if current_user_id and post.author_id == current_user_id:
            return post

        return None
    
    @staticmethod
    async def get_posts(
        session: AsyncSession,
        page: int = 1,
        limit: int = 10,
        status_filter: Optional[PostStatus] = PostStatus.PUBLISHED,
        include_author: bool = True,
        search: Optional[str] = None
    ) -> Tuple[List[Post], int]:
        """Get paginated list of posts

        Args:
            session: Database session
            page: Page number (1-indexed)
            limit: Number of posts per page
            status_filter: Filter by post status
            include_author: Include author relation
            search: Search term to filter posts by title or content

        Returns:
            Tuple of (posts, total_count)
        """
        # Build base query - exclude soft-deleted posts
        query = select(Post).where(Post.deleted_at.is_(None))
        count_query = select(func.count()).select_from(Post).where(Post.deleted_at.is_(None))

        # Apply status filter
        if status_filter is not None:
            query = query.where(Post.status == status_filter)
            count_query = count_query.where(Post.status == status_filter)

        # Apply search filter
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            search_condition = Post.title.ilike(search_term) | Post.content.ilike(search_term)
            query = query.where(search_condition)
            count_query = count_query.where(search_condition)

        # Include author and tags relations to avoid N+1 queries
        if include_author:
            query = query.options(joinedload(Post.author))

        # Always include tags
        query = query.options(selectinload(Post.tags))

        # Order by created_at descending (newest first)
        query = query.order_by(desc(Post.created_at))

        # Get total count
        total_count_result = await session.execute(count_query)
        total_count = total_count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await session.execute(query)
        posts = result.scalars().unique().all()

        return posts, total_count
    
    @staticmethod
    async def get_post_with_permission_check(
        session: AsyncSession,
        post_id: int,
        current_user_id: Optional[int] = None
    ) -> Optional[Post]:
        """Get a post with permission check
        
        - Published posts are visible to everyone
        - Draft/archived posts are only visible to their authors
        - Soft-deleted posts are not visible
        """
        stmt = select(Post).options(
            joinedload(Post.author),
            selectinload(Post.tags)
        ).where(
            Post.id == post_id,
            Post.deleted_at.is_(None)  # Exclude soft-deleted posts
        )
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()
        
        if not post:
            return None
        
        # Check permissions
        if post.status == PostStatus.PUBLISHED:
            return post
        
        # Draft or archived posts - only visible to author
        if current_user_id and post.author_id == current_user_id:
            return post
        
        return None
    
    @staticmethod
    async def _get_tag_by_slug(session: AsyncSession, slug: str) -> Optional[Tag]:
        """Helper method to get tag by slug"""
        result = await session.execute(
            select(Tag).where(Tag.slug == slug)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _build_posts_by_tag_query(tag_id: int):
        """Helper method to build query for posts by tag"""
        return (
            select(Post)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                and_(
                    post_tags.c.tag_id == tag_id,
                    Post.deleted_at.is_(None),
                    Post.status == PostStatus.PUBLISHED
                )
            )
            .options(
                joinedload(Post.author),
                selectinload(Post.tags)
            )
            .order_by(desc(Post.created_at))
        )
    
    @staticmethod
    async def _count_posts_by_tag(session: AsyncSession, tag_id: int) -> int:
        """Helper method to count posts by tag"""
        query = (
            select(func.count())
            .select_from(Post)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                and_(
                    post_tags.c.tag_id == tag_id,
                    Post.deleted_at.is_(None),
                    Post.status == PostStatus.PUBLISHED
                )
            )
        )
        result = await session.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_posts_by_tag(
        session: AsyncSession,
        tag_slug: str,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[Post], int]:
        """Get posts filtered by tag slug"""
        # Get the tag
        tag = await PostService._get_tag_by_slug(session, tag_slug)
        if not tag:
            return [], 0
        
        # Build and execute query
        query = PostService._build_posts_by_tag_query(tag.id)
        
        # Get total count
        total_count = await PostService._count_posts_by_tag(session, tag.id)
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute and return results
        result = await session.execute(query)
        posts = result.scalars().unique().all()
        
        return posts, total_count
    
    @staticmethod
    async def _get_tag_ids_by_slugs(session: AsyncSession, slugs: List[str]) -> List[int]:
        """Helper method to get tag IDs by slugs"""
        result = await session.execute(
            select(Tag.id).where(Tag.slug.in_(slugs))
        )
        return [row[0] for row in result]
    
    @staticmethod
    def _build_posts_with_all_tags_query(tag_ids: List[int]):
        """Build query for posts that have ALL specified tags"""
        # First get post IDs that have all tags
        post_ids_subquery = (
            select(Post.id)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                and_(
                    post_tags.c.tag_id.in_(tag_ids),
                    Post.deleted_at.is_(None),
                    Post.status == PostStatus.PUBLISHED
                )
            )
            .group_by(Post.id)
            .having(func.count(post_tags.c.tag_id) == len(tag_ids))
            .subquery()
        )
        
        # Then get full posts
        return (
            select(Post)
            .where(Post.id.in_(select(post_ids_subquery.c.id)))
            .options(
                joinedload(Post.author),
                selectinload(Post.tags)
            )
            .order_by(desc(Post.created_at))
        )
    
    @staticmethod
    def _build_posts_with_any_tags_query(tag_ids: List[int]):
        """Build query for posts that have ANY of the specified tags"""
        return (
            select(Post)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                and_(
                    post_tags.c.tag_id.in_(tag_ids),
                    Post.deleted_at.is_(None),
                    Post.status == PostStatus.PUBLISHED
                )
            )
            .distinct()
            .options(
                joinedload(Post.author),
                selectinload(Post.tags)
            )
            .order_by(desc(Post.created_at))
        )
    
    @staticmethod
    async def _count_posts_with_all_tags(session: AsyncSession, tag_ids: List[int]) -> int:
        """Count posts that have ALL specified tags"""
        count_subquery = (
            select(Post.id)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                and_(
                    post_tags.c.tag_id.in_(tag_ids),
                    Post.deleted_at.is_(None),
                    Post.status == PostStatus.PUBLISHED
                )
            )
            .group_by(Post.id)
            .having(func.count(post_tags.c.tag_id) == len(tag_ids))
            .subquery()
        )
        
        result = await session.execute(
            select(func.count()).select_from(count_subquery)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def _count_posts_with_any_tags(session: AsyncSession, tag_ids: List[int]) -> int:
        """Count posts that have ANY of the specified tags"""
        query = (
            select(func.count(Post.id.distinct()))
            .select_from(Post)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                and_(
                    post_tags.c.tag_id.in_(tag_ids),
                    Post.deleted_at.is_(None),
                    Post.status == PostStatus.PUBLISHED
                )
            )
        )
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_posts_by_tags(
        session: AsyncSession,
        tag_slugs: List[str],
        require_all: bool = False,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[Post], int]:
        """Get posts filtered by multiple tags

        Args:
            tag_slugs: List of tag slugs to filter by
            require_all: If True, posts must have ALL tags. If False, posts with ANY tag match
        """
        # Get tag IDs
        tag_ids = await PostService._get_tag_ids_by_slugs(session, tag_slugs)
        if not tag_ids:
            return [], 0

        # Build query based on require_all flag
        if require_all:
            query = PostService._build_posts_with_all_tags_query(tag_ids)
            total_count = await PostService._count_posts_with_all_tags(session, tag_ids)
        else:
            query = PostService._build_posts_with_any_tags_query(tag_ids)
            total_count = await PostService._count_posts_with_any_tags(session, tag_ids)

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # Execute and return results
        result = await session.execute(query)
        posts = result.scalars().unique().all()

        return posts, total_count

    # ========== Update Post Methods ==========

    @staticmethod
    async def _get_post_for_update(
        session: AsyncSession, post_id: int, author_id: int
    ) -> Post:
        """獲取 post 並驗證權限"""
        result = await session.execute(
            select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise ValueError("Post not found")
        if post.author_id != author_id:
            raise ValueError("You don't have permission to edit this post")
        return post

    @staticmethod
    def _apply_field_updates(
        post: Post,
        title: Optional[str],
        content: Optional[str],
        excerpt: Optional[str],
        status: Optional[str]
    ) -> None:
        """套用欄位更新"""
        if title is not None:
            if not title.strip():
                raise ValueError("Title cannot be empty")
            post.title = title.strip()

        if content is not None:
            if not content.strip():
                raise ValueError("Content cannot be empty")
            post.content = content

        if excerpt is not None:
            post.excerpt = excerpt

        if status is not None:
            post.status = status
            if status == PostStatus.PUBLISHED.value and not post.published_at:
                post.published_at = datetime.now(timezone.utc)

    @staticmethod
    async def _apply_slug_update(
        session: AsyncSession, post: Post, slug: Optional[str]
    ) -> None:
        """套用 slug 更新（含唯一性檢查）"""
        if slug is None:
            return
        existing = await session.execute(
            select(Post).where(Post.slug == slug, Post.id != post.id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Slug already exists")
        post.slug = slug

    @staticmethod
    async def _reload_post_with_relations(session: AsyncSession, post_id: int) -> Post:
        """重新載入 post 及其關聯"""
        result = await session.execute(
            select(Post)
            .options(selectinload(Post.tags), joinedload(Post.author))
            .where(Post.id == post_id)
        )
        return result.scalar_one()

    @staticmethod
    async def update_post(
        session: AsyncSession,
        post_id: int,
        author_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        excerpt: Optional[str] = None,
        status: Optional[str] = None,
        slug: Optional[str] = None
    ) -> Post:
        """更新文章"""
        post = await PostService._get_post_for_update(session, post_id, author_id)
        PostService._apply_field_updates(post, title, content, excerpt, status)
        await PostService._apply_slug_update(session, post, slug)
        post.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return await PostService._reload_post_with_relations(session, post.id)