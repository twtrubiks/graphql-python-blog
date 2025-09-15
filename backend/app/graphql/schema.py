import strawberry
from typing import Optional, List
from app.graphql.mutations.auth import register, login, AuthPayload
from app.graphql.mutations.post import (
    create_post,
    update_post,
    delete_post,
    publish_post,
    unpublish_post,
    DeletePostResult
)
from app.graphql.mutations.comment import CommentMutation
from app.graphql.mutations.like import LikeMutation
from app.graphql.mutations.follow import FollowMutation
from app.graphql.queries.auth import me, protected_data, ProtectedData
from app.graphql.queries.user import get_user, get_users
from app.graphql.queries.post import PostQuery
from app.graphql.types.user import UserType
from app.graphql.types.post import PostType
from app.graphql.subscriptions.comment import CommentSubscription
from app.graphql.subscriptions.user_status import UserStatusSubscription


@strawberry.type
class Query(PostQuery):
    @strawberry.field
    def hello(self, name: Optional[str] = None) -> str:
        return f"Hello {name or 'World'}!"

    @strawberry.field
    def version(self) -> str:
        return "1.0.0"

    me: Optional[UserType] = strawberry.field(resolver=me)
    protectedData: ProtectedData = strawberry.field(resolver=protected_data, name="protectedData")
    user: Optional[UserType] = strawberry.field(resolver=get_user)
    users: List[UserType] = strawberry.field(resolver=get_users)


@strawberry.type
class Mutation(CommentMutation, LikeMutation, FollowMutation):
    register: AuthPayload = strawberry.field(resolver=register)
    login: AuthPayload = strawberry.field(resolver=login)

    # Post mutations
    create_post: PostType = strawberry.field(resolver=create_post)
    update_post: PostType = strawberry.field(resolver=update_post)
    delete_post: DeletePostResult = strawberry.field(resolver=delete_post)
    publish_post: PostType = strawberry.field(resolver=publish_post)
    unpublish_post: PostType = strawberry.field(resolver=unpublish_post)

    @strawberry.mutation
    def echo(self, message: str) -> str:
        return f"Echo: {message}"


@strawberry.type
class Subscription(CommentSubscription, UserStatusSubscription):
    pass


schema = strawberry.Schema(
    query=Query, 
    mutation=Mutation,
    subscription=Subscription
)