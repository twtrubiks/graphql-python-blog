"""Post GraphQL queries"""

from typing import Optional, List
import strawberry
from strawberry.types import Info

from app.graphql.types.post import PostType, PostConnection, PostEdge, PageInfo
from app.services.post import PostService
from app.core.auth import get_current_user_optional


@strawberry.type
class PostQuery:
    @strawberry.field
    async def post(
        self,
        info: Info,
        id: strawberry.ID
    ) -> Optional[PostType]:
        """Get a single post by ID"""
        session = info.context["db_session"]
        
        # Get current user if authenticated
        user = await get_current_user_optional(info)
        current_user_id = user.id if user else None
        
        # Get post with permission check
        post = await PostService.get_post_with_permission_check(
            session,
            int(id),
            current_user_id
        )
        
        return PostType.from_orm(post) if post else None
    
    @strawberry.field
    async def posts(
        self,
        info: Info,
        page: int = 1,
        limit: int = 10
    ) -> PostConnection:
        """Get paginated list of published posts"""
        session = info.context["db_session"]
        
        # Get posts (only published ones for public access)
        posts, total_count = await PostService.get_posts(
            session,
            page=page,
            limit=limit
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next_page = page < total_pages
        has_previous_page = page > 1
        
        # Create edges
        edges = [
            PostEdge(
                node=PostType.from_orm(post)
            )
            for post in posts
        ]
        
        # Create page info
        page_info = PageInfo(
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            total_count=total_count,
            current_page=page,
            total_pages=total_pages
        )
        
        return PostConnection(
            edges=edges,
            page_info=page_info
        )