import strawberry
from typing import Union, Annotated

from app.graphql.types.post import PostType
from app.graphql.types.user import UserType


SearchResult = Annotated[
    Union[PostType, UserType],
    strawberry.union("SearchResult")
]