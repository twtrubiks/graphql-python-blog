from __future__ import annotations
import strawberry
from typing import Optional, List, Annotated
from datetime import datetime
from enum import Enum
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.graphql.types.tag import TagType
from app.models.post import Post as PostModel


@strawberry.enum
class PostStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@strawberry.type
class PostType:
    id: int
    title: str
    slug: str
    content: str
    status: PostStatus
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    author_id: int
    _author: strawberry.Private[Optional[object]] = None
    _excerpt: strawberry.Private[Optional[str]] = None
    _tags: strawberry.Private[Optional[List[object]]] = None
    
    @strawberry.field
    def excerpt(self) -> str:
        """Generate excerpt from content or use provided excerpt"""
        # Get the actual excerpt from the database model if it exists
        if self._excerpt:
            return self._excerpt
        # Otherwise, generate from content
        if self.content:
            max_length = 150
            if len(self.content) > max_length:
                return self.content[:max_length] + "..."
            return self.content
        return ""
    
    @strawberry.field
    async def author(self, info: strawberry.Info) -> Annotated["UserType", strawberry.lazy("app.graphql.types.user")]:
        """Resolve author relationship"""
        from app.graphql.types.user import UserType
        from app.services.user import UserService
        
        # If author was preloaded, use it
        if self._author:
            return UserType.from_orm(self._author)
        
        # Otherwise, fetch from database
        session = info.context["db_session"]
        user = await UserService.get_user_by_id(session, self.author_id)
        return UserType.from_orm(user) if user else None

    @strawberry.field
    def createdAt(self) -> datetime:
        return self.created_at

    @strawberry.field
    def updatedAt(self) -> datetime:
        return self.updated_at

    @strawberry.field
    def publishedAt(self) -> Optional[datetime]:
        return self.published_at
    
    @strawberry.field
    async def tags(self, info: strawberry.Info) -> List[TagType]:
        """Resolve tags relationship"""
        # If tags were preloaded, use them
        if self._tags is not None:
            return [TagType.from_model(tag) for tag in self._tags]
        
        # Otherwise, fetch from database
        session = info.context["db_session"]
        result = await session.execute(
            select(PostModel)
            .options(selectinload(PostModel.tags))
            .where(PostModel.id == self.id)
        )
        post = result.scalar_one_or_none()
        
        if post and post.tags:
            return [TagType.from_model(tag) for tag in post.tags]
        return []
    
    @classmethod
    def from_orm(cls, post):
        """Create PostType from ORM model"""
        return cls(
            id=post.id,
            title=post.title,
            slug=post.slug,
            content=post.content,
            _excerpt=post.excerpt,  # Store the actual excerpt
            _author=getattr(post, 'author', None),  # Store preloaded author if exists
            _tags=getattr(post, 'tags', None),  # Store preloaded tags if exists
            status=PostStatus(post.status.value if hasattr(post.status, 'value') else post.status),
            author_id=post.author_id,
            created_at=post.created_at,
            updated_at=post.updated_at,
            published_at=post.published_at
        )


@strawberry.type
class PageInfo:
    """Pagination information"""
    has_next_page: bool
    has_previous_page: bool
    total_count: int
    current_page: int
    total_pages: int


@strawberry.type
class PostEdge:
    """Edge for post in connection"""
    node: PostType


@strawberry.type
class PostConnection:
    """Paginated post connection"""
    edges: List[PostEdge]
    page_info: PageInfo


@strawberry.input
class PostInput:
    title: str
    content: str
    excerpt: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[PostStatus] = PostStatus.DRAFT


@strawberry.input
class UpdatePostInput:
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[PostStatus] = None
