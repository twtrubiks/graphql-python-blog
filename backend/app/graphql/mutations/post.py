import strawberry
from typing import Optional
from strawberry.types import Info
from app.graphql.types.post import PostType, PostInput, PostStatus
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
    
    # Convert to GraphQL type
    return PostType(
        id=post.id,
        title=post.title,
        slug=post.slug,
        content=post.content,
        excerpt=post.excerpt,
        status=PostStatus(post.status.value),
        author=current_user,
        created_at=post.created_at,
        updated_at=post.updated_at,
        published_at=post.published_at
    )