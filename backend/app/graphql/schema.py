import strawberry
from typing import Optional


@strawberry.type
class User:
    id: int
    username: str
    email: str
    bio: Optional[str] = None


@strawberry.type
class Post:
    id: int
    title: str
    content: str
    excerpt: Optional[str] = None
    author: User


@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: Optional[str] = None) -> str:
        return f"Hello {name or 'World'}!"
    
    @strawberry.field
    def version(self) -> str:
        return "1.0.0"


@strawberry.type
class Mutation:
    @strawberry.mutation
    def echo(self, message: str) -> str:
        return f"Echo: {message}"


schema = strawberry.Schema(query=Query, mutation=Mutation)