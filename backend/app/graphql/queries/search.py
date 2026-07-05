import strawberry
from typing import List
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user import User
from app.graphql.types.search import SearchResult
from app.graphql.types.post import PostType
from app.graphql.types.user import UserType


@strawberry.type
class SearchQuery:
    @strawberry.field
    async def search(
        self,
        term: str,
        info: strawberry.Info
    ) -> List[SearchResult]:
        """搜尋文章和用戶"""
        db: AsyncSession = info.context["db_session"]
        results: List[SearchResult] = []

        # 搜尋詞轉小寫以進行不區分大小寫的搜尋
        search_term = term.lower()

        # 搜尋文章（只搜尋已發布且未被軟刪除的）
        post_stmt = select(Post).where(
            or_(
                func.lower(Post.title).contains(search_term),
                func.lower(Post.content).contains(search_term),
                func.lower(Post.excerpt).contains(search_term)
            ),
            Post.status == "published",
            Post.deleted_at.is_(None)
        )

        post_result = await db.execute(post_stmt)
        posts = post_result.scalars().all()

        # 將文章轉換為 PostType
        for post in posts:
            post_type = PostType(
                id=post.id,
                title=post.title,
                slug=post.slug,
                content=post.content,
                status=post.status,
                author_id=post.author_id,
                published_at=post.published_at,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
            # Set the private excerpt field
            post_type._excerpt = post.excerpt
            results.append(post_type)

        # 搜尋用戶
        user_stmt = select(User).where(
            or_(
                func.lower(User.username).contains(search_term),
                func.lower(User.bio).contains(search_term) if User.bio else False
            )
        )

        user_result = await db.execute(user_stmt)
        users = user_result.scalars().all()

        # 將用戶轉換為 UserType
        for user in users:
            results.append(UserType(
                id=str(user.id),
                email=user.email,
                username=user.username,
                bio=user.bio,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=user.created_at
            ))

        return results