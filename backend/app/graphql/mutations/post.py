import strawberry
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select
from strawberry.types import Info

from app.models.post import Post
from app.graphql.types.post import PostType, PostInput, UpdatePostInput, PostStatus
from app.services.post import PostService
from app.core.auth import require_auth


async def create_post(
    info: Info,
    input: PostInput
) -> PostType:
    """Create a new post (requires authentication)"""
    
    # Check authentication
    current_user = await require_auth(info)
    
    # Get database session
    session = info.context["db_session"]
    
    # Validate input
    if not input.title or not input.title.strip():
        raise ValueError("Title cannot be empty")
    
    if not input.content or not input.content.strip():
        raise ValueError("Content cannot be empty")
    
    # Convert status enum if needed
    status_value = input.status.value if input.status else PostStatus.DRAFT.value
    
    # Create the post
    post = await PostService.create_post(
        session=session,
        title=input.title.strip(),
        content=input.content,
        author_id=current_user.id,
        excerpt=input.excerpt,
        slug=input.slug,
        status=status_value
    )
    
    # Load author relationship
    await session.refresh(post)
    
    # Convert to GraphQL type using from_orm method
    return PostType.from_orm(post)


async def update_post(
    info: Info,
    id: strawberry.ID,
    input: UpdatePostInput
) -> PostType:
    """Update an existing post (author only)"""
    
    # Check authentication
    current_user = await require_auth(info)
    
    # Get database session
    session = info.context["db_session"]
    
    # Get the post (exclude soft-deleted)
    result = await session.execute(
        select(Post).where(
            Post.id == int(id),
            Post.deleted_at.is_(None)
        )
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise ValueError("Post not found")
    
    # Check if current user is the author
    if post.author_id != current_user.id:
        raise ValueError("You don't have permission to edit this post")
    
    # Update fields that are provided
    if input.title is not None:
        if not input.title.strip():
            raise ValueError("Title cannot be empty")
        post.title = input.title.strip()
    
    if input.content is not None:
        if not input.content.strip():
            raise ValueError("Content cannot be empty")
        post.content = input.content
    
    if input.excerpt is not None:
        post.excerpt = input.excerpt
    
    if input.status is not None:
        post.status = input.status.value
        # If changing to PUBLISHED and no published_at, set it
        if input.status == PostStatus.PUBLISHED and not post.published_at:
            post.published_at = datetime.now(timezone.utc)
    
    if input.slug is not None:
        # Check if new slug is unique
        existing = await session.execute(
            select(Post).where(
                Post.slug == input.slug,
                Post.id != post.id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Slug already exists")
        post.slug = input.slug
    
    # Update the updatedAt timestamp
    post.updated_at = datetime.now(timezone.utc)
    
    # Save changes
    await session.commit()
    await session.refresh(post)
    
    return PostType.from_orm(post)


@strawberry.type
class DeletePostResult:
    success: bool
    message: str


async def delete_post(
    info: Info,
    id: strawberry.ID
) -> DeletePostResult:
    """Delete a post (author only)"""
    
    # Check authentication
    current_user = await require_auth(info)
    
    # Get database session
    session = info.context["db_session"]
    
    # Get the post (exclude soft-deleted)
    result = await session.execute(
        select(Post).where(
            Post.id == int(id),
            Post.deleted_at.is_(None)
        )
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise ValueError("Post not found")
    
    # Check if current user is the author
    if post.author_id != current_user.id:
        raise ValueError("You don't have permission to delete this post")
    
    # Implement soft delete
    # Check if Post model has soft delete fields
    if hasattr(Post, 'deleted_at'):
        post.deleted_at = datetime.now(timezone.utc)
    elif hasattr(Post, 'is_deleted'):
        post.is_deleted = True
    else:
        # If no soft delete fields, do hard delete
        await session.delete(post)
    
    await session.commit()
    
    return DeletePostResult(
        success=True,
        message="Post deleted successfully"
    )