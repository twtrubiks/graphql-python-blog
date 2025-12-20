"""Post GraphQL queries"""

from typing import Optional, List
import strawberry
from strawberry.types import Info

from app.graphql.types.post import PostType, PostConnection, PostEdge, PageInfo
from app.services.post import PostService
from app.services.user import UserService
from app.core.auth import get_current_user_optional, require_auth
from app.graphql.permissions import IsAuthenticated


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
        limit: int = 10,
        search: Optional[str] = None
    ) -> PostConnection:
        """Get paginated list of published posts

        Args:
            page: Page number (1-indexed)
            limit: Number of posts per page
            search: Search term to filter posts by title or content
        """
        session = info.context["db_session"]

        # Get posts (only published ones for public access)
        posts, total_count = await PostService.get_posts(
            session,
            page=page,
            limit=limit,
            search=search
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

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def following_posts(
        self,
        info: Info,
        page: int = 1,
        limit: int = 10
    ) -> PostConnection:
        """
        Get posts from users that the current user follows

        Only shows published posts from followed users.
        Requires authentication.

        Args:
            page: Page number (1-indexed)
            limit: Number of posts per page

        Returns:
            PostConnection with paginated posts from followed users
        """
        session = info.context["db_session"]

        # Get current user
        current_user = await require_auth(info)

        # Get posts from followed users
        posts, total_count = await PostService.get_posts_by_followed_users(
            session,
            user_id=current_user.id,
            page=page,
            limit=limit
        )

        return PostQuery._create_connection(posts, total_count, page, limit)

    @strawberry.field(permission_classes=[IsAuthenticated])
    async def my_posts(
        self,
        info: Info,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None
    ) -> PostConnection:
        """
        Get current user's posts (both published and drafts)

        Args:
            page: Page number (1-indexed)
            limit: Number of posts per page
            status: Filter by status ('PUBLISHED', 'DRAFT', or None for all)

        Returns:
            PostConnection with paginated posts by current user
        """
        session = info.context["db_session"]

        # Get current user
        current_user = await require_auth(info)

        # Get posts by author
        posts, total_count = await PostService.get_posts_by_author(
            session,
            author_id=current_user.id,
            status=status,
            page=page,
            limit=limit
        )

        return PostQuery._create_connection(posts, total_count, page, limit)

    @strawberry.field
    async def posts_by_author(
        self,
        info: Info,
        author_id: Optional[int] = None,
        author_username: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> PostConnection:
        """
        Get published posts by a specific author (public)

        Args:
            author_id: Author's user ID
            author_username: Author's username
            page: Page number (1-indexed)
            limit: Number of posts per page

        Returns:
            PostConnection with paginated published posts by the author
        """
        if not author_id and not author_username:
            raise ValueError("Either author_id or author_username must be provided")

        session = info.context["db_session"]

        # If username provided, look up the author_id
        if author_username and not author_id:
            user = await UserService.get_user_by_username(session, author_username)
            if not user:
                # Return empty connection if user not found
                return PostQuery._create_connection([], 0, page, limit)
            author_id = user.id

        # Get only published posts by author
        posts, total_count = await PostService.get_posts_by_author(
            session,
            author_id=author_id,
            status="PUBLISHED",
            page=page,
            limit=limit
        )

        return PostQuery._create_connection(posts, total_count, page, limit)