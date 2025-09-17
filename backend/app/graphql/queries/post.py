"""Post GraphQL queries"""

from typing import Optional, List
import strawberry
from strawberry.types import Info

from app.graphql.types.post import PostType, PostConnection, PostEdge, PageInfo
from app.services.post import PostService
from app.core.auth import get_current_user_optional


@strawberry.type
class PostQuery:
    @staticmethod
    def _create_connection(
        posts: List,
        total_count: int,
        page: int,
        limit: int
    ) -> PostConnection:
        """Helper method to create PostConnection with pagination info"""
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        has_next_page = page < total_pages
        has_previous_page = page > 1
        
        # Create edges
        edges = [
            PostEdge(node=PostType.from_orm(post))
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
    
    @strawberry.field
    async def post(
        self,
        info: Info,
        id: Optional[strawberry.ID] = None,
        slug: Optional[str] = None
    ) -> Optional[PostType]:
        """Get a single post by ID or slug"""
        if not id and not slug:
            raise ValueError("Either id or slug must be provided")

        session = info.context["db_session"]

        # Get current user if authenticated
        user = await get_current_user_optional(info)
        current_user_id = user.id if user else None

        # Get post by ID or slug
        if id:
            # Try to parse as integer ID
            try:
                post = await PostService.get_post_with_permission_check(
                    session,
                    int(id),
                    current_user_id
                )
            except ValueError:
                # If not a valid integer, treat it as slug
                post = await PostService.get_post_by_slug(
                    session,
                    str(id),
                    current_user_id
                )
        else:
            # Get by slug
            post = await PostService.get_post_by_slug(
                session,
                slug,
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
        
        return PostQuery._create_connection(posts, total_count, page, limit)
    
    @strawberry.field
    async def posts_by_tag(
        self,
        info: Info,
        tag_slug: str,
        page: int = 1,
        limit: int = 10
    ) -> PostConnection:
        """Get posts filtered by a single tag"""
        session = info.context["db_session"]
        
        # Get posts with the specified tag
        posts, total_count = await PostService.get_posts_by_tag(
            session,
            tag_slug=tag_slug,
            page=page,
            limit=limit
        )
        
        return PostQuery._create_connection(posts, total_count, page, limit)
    
    @strawberry.field
    async def posts_by_tags(
        self,
        info: Info,
        tag_slugs: List[str],
        require_all: bool = False,
        page: int = 1,
        limit: int = 10
    ) -> PostConnection:
        """Get posts filtered by multiple tags"""
        session = info.context["db_session"]
        
        # Get posts with the specified tags
        posts, total_count = await PostService.get_posts_by_tags(
            session,
            tag_slugs=tag_slugs,
            require_all=require_all,
            page=page,
            limit=limit
        )
        
        return PostQuery._create_connection(posts, total_count, page, limit)