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
