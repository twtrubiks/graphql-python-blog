import strawberry
from typing import Optional, TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from app.graphql.types.post import PostType


@strawberry.type
class LikeMutationResponse:
    """按讚操作回應"""
    success: bool
    message: str
    post: Optional[Annotated["PostType", strawberry.lazy("app.graphql.types.post")]] = None
    
    @classmethod
    def create(cls, success: bool, message: str, post=None):
        from app.graphql.types.post import PostType
        if post:
            post_type = PostType.from_orm(post)
            return cls(success=success, message=message, post=post_type)
        return cls(success=success, message=message)