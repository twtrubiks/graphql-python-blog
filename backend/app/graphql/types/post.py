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
    _comments: strawberry.Private[Optional[List[object]]] = None
    
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
        
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            user = await dataloaders.get_user_loader().load(self.author_id)
            return UserType.from_orm(user) if user else None
        
        # Fallback to direct database query
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

        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            tags = await dataloaders.get_post_tags_loader().load(self.id)
            return [TagType.from_model(tag) for tag in tags]

        # Fallback to direct database query
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
    
    @strawberry.field
    async def comments(
        self, 
        info: strawberry.Info,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Annotated["Comment", strawberry.lazy("app.graphql.types.comment")]]:
        """Resolve comments relationship with pagination"""
        from app.graphql.types.comment import Comment
        from app.services.comment import CommentService
        
        # Check if DataLoader is available and no pagination is requested
        dataloaders = info.context.get("dataloaders")
        if dataloaders and limit is None and offset is None:
            # Use DataLoader for batching when no pagination
            comments = await dataloaders.get_post_comments_loader().load(self.id)
        else:
            # Fallback to direct query for paginated results
            session = info.context["db_session"]
            comments = await CommentService.get_post_comments(
                db=session,
                post_id=self.id,
                limit=limit,
                offset=offset
            )
        
        # Convert to GraphQL types
        return [
            Comment(
                id=str(comment.id),
                content=comment.content,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                deleted_at=comment.deleted_at,
                author=comment.author,
                post=None  # Avoid circular reference
            )
            for comment in comments
        ]
    
    @strawberry.field
    async def total_comments(self, info: strawberry.Info) -> int:
        """Get total comment count for this post"""
        from app.services.comment import CommentService

        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            return await dataloaders.get_comment_count_loader().load(self.id)

        # Fallback to direct database query
        session = info.context["db_session"]
        return await CommentService.get_comment_count(session, self.id)
    
    @strawberry.field
    async def likes_count(self, info: strawberry.Info) -> int:
        """Get total likes count for this post"""
        from app.services.like import LikeService
        
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            return await dataloaders.get_like_count_loader().load(self.id)
        
        # Fallback to direct database query
        session = info.context["db_session"]
        return await LikeService.get_post_likes_count(session, self.id)
    
    @strawberry.field
    async def is_liked(self, info: strawberry.Info) -> bool:
        """Check if current user has liked this post"""
        from app.services.like import LikeService
        from app.core.deps import get_current_user_id
        
        # Check if DataLoader is available
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            # Use DataLoader for batching
            return await dataloaders.get_user_liked_posts_loader().load(self.id)
        
        # Fallback to direct database query
        session = info.context["db_session"]
        user_id = await get_current_user_id(info)
        return await LikeService.is_post_liked_by_user(session, self.id, user_id)
    
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
    tags: Optional[List[str]] = None


@strawberry.input
class UpdatePostInput:
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[PostStatus] = None
    tags: Optional[List[str]] = None
