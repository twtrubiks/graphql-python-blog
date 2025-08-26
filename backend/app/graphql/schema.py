import strawberry
from typing import Optional
from app.graphql.mutations.auth import register, login, AuthPayload
from app.graphql.queries.auth import me, protected_data, ProtectedData
from app.graphql.types.user import UserType


@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: Optional[str] = None) -> str:
        return f"Hello {name or 'World'}!"
    
    @strawberry.field
    def version(self) -> str:
        return "1.0.0"
    
    me: Optional[UserType] = strawberry.field(resolver=me)
    protectedData: ProtectedData = strawberry.field(resolver=protected_data, name="protectedData")


@strawberry.type
class Mutation:
    register: AuthPayload = strawberry.field(resolver=register)
    login: AuthPayload = strawberry.field(resolver=login)
    
    @strawberry.mutation
    def echo(self, message: str) -> str:
        return f"Echo: {message}"


schema = strawberry.Schema(query=Query, mutation=Mutation)