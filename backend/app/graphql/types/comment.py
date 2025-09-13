import strawberry
from typing import Optional
from datetime import datetime


@strawberry.type
class Comment:
    id: strawberry.ID
    content: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    # Relations - will be resolved by field resolvers
    author: Optional["UserType"] = None
    post: Optional["PostType"] = None
    
    @strawberry.field
    def is_deleted(self) -> bool:
        """檢查評論是否已被軟刪除"""
        return self.deleted_at is not None


@strawberry.input
class CommentInput:
    content: str


@strawberry.type
class CommentMutationResponse:
    success: bool
    message: Optional[str] = None
    comment: Optional[Comment] = None


# Forward declarations for circular imports
from app.graphql.types.user import UserType
from app.graphql.types.post import PostType