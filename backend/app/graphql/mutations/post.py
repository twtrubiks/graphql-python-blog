import strawberry
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from strawberry.types import Info
import asyncio

from app.models.post import Post
from app.graphql.types.post import PostType, PostInput, UpdatePostInput, PostStatus
from app.services.post import PostService
from app.services.follow import FollowService
from app.core.auth import require_auth
from app.graphql.subscriptions.post import PostEvent
from app.graphql.subscriptions.followed_user_post import FollowedUserPostEvent


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

    # Post is already loaded with relationships from PostService
    return PostType.from_orm(post)


async def update_post(
    info: Info,
    id: strawberry.ID,
    input: UpdatePostInput
) -> PostType:
    """Update an existing post (author only)"""
    current_user = await require_auth(info)
    session = info.context["db_session"]

    post = await PostService.update_post(
        session=session,
        post_id=int(id),
        author_id=current_user.id,
        title=input.title,
        content=input.content,
        excerpt=input.excerpt,
        status=input.status.value if input.status else None,
        slug=input.slug
    )

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


async def publish_post(
    info: Info,
    id: strawberry.ID
) -> PostType:
    """Publish a post (author only)"""

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
        raise ValueError("You don't have permission to publish this post")

    # Check if already published
    if post.status == PostStatus.PUBLISHED.value:
        raise ValueError("Post is already published")

    # Update status and published_at
    post.status = PostStatus.PUBLISHED.value
    post.published_at = datetime.now(timezone.utc)
    post.updated_at = datetime.now(timezone.utc)

    # Save changes
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
    post = result.scalar_one()

    # 轉換為 PostType
    post_type = PostType.from_orm(post)

    # 觸發全域 subscription 事件 (非同步執行，不等待)
    asyncio.create_task(PostEvent.publish_post(post_type))

    # 觸發追蹤用戶發文通知 (非同步執行，不等待)
    async def notify_followers():
        # 查詢作者的所有追蹤者
        follower_ids = await FollowService.get_follower_ids(session, post.author_id)
        if follower_ids:
            await FollowedUserPostEvent.publish_to_followers(follower_ids, post_type)

    asyncio.create_task(notify_followers())

    return post_type


async def unpublish_post(
    info: Info,
    id: strawberry.ID
) -> PostType:
    """Unpublish a post (author only)"""

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
        raise ValueError("You don't have permission to unpublish this post")

    # Check if not published
    if post.status != PostStatus.PUBLISHED.value:
        raise ValueError("Post is not published")

    # Update status and clear published_at
    post.status = PostStatus.DRAFT.value
    post.published_at = None
    post.updated_at = datetime.now(timezone.utc)

    # Save changes
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
    post = result.scalar_one()

    return PostType.from_orm(post)