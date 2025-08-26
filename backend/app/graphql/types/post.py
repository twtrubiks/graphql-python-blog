import strawberry
from typing import Optional
from datetime import datetime
from enum import Enum
from app.graphql.types.user import UserType


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
    excerpt: Optional[str]
    status: PostStatus
    author: UserType
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    @strawberry.field
    def createdAt(self) -> datetime:
        return self.created_at

    @strawberry.field
    def updatedAt(self) -> datetime:
        return self.updated_at

    @strawberry.field
    def publishedAt(self) -> Optional[datetime]:
        return self.published_at


@strawberry.input
class PostInput:
    title: str
    content: str
    excerpt: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[PostStatus] = PostStatus.DRAFT
