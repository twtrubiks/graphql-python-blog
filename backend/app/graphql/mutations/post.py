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
from app.graphql.subscriptions.post_deleted import PostDeletedEvent
from app.core.database import AsyncSessionLocal


async def _notify_post_published(author_id: int, post_type: PostType):
    """
    發布文章後觸發通知（使用獨立 session 避免狀態衝突）

    Args:
        author_id: 文章作者 ID（用於查詢追蹤者）
        post_type: PostType GraphQL 型別（用於推送給訂閱者）
    """
    # 觸發全域 subscription 事件
    asyncio.create_task(PostEvent.publish_post(post_type))

    # 觸發追蹤用戶發文通知（使用獨立 session）
    async def notify_followers():
        async with AsyncSessionLocal() as session:
            follower_ids = await FollowService.get_follower_ids(session, author_id)
            if follower_ids:
                await FollowedUserPostEvent.publish_to_followers(follower_ids, post_type)

    asyncio.create_task(notify_followers())


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
        status=status_value,
        tag_names=input.tags
    )

    post_type = PostType.from_orm(post)

    # 如果直接發布，觸發通知
    if status_value == PostStatus.PUBLISHED.value:
        await _notify_post_published(post.author_id, post_type)

    return post_type


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
        slug=input.slug,
        tag_names=input.tags
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

    # 保存刪除前的資訊（commit 後可能無法存取）
    author_id = post.author_id
    post_id = post.id

    # 在 commit 前獲取追蹤者 ID（session 仍然有效）
    follower_ids = await FollowService.get_follower_ids(session, author_id)

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

    # 後台發送通知（純記憶體操作，不需要 session）
    if follower_ids:
        async def safe_notify():
            try:
                await PostDeletedEvent.publish_to_followers(follower_ids, post_id)
            except Exception as e:
                import logging
                logging.error(f"Failed to notify followers about deleted post {post_id}: {e}")

        asyncio.create_task(safe_notify())

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

    # 觸發通知（失敗不影響主流程）
    try:
        await _notify_post_published(post.author_id, post_type)
    except Exception as e:
        # 通知失敗不應該影響發布操作
        print(f"Warning: Failed to send publish notification: {e}")

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