"""Tag GraphQL types"""

from datetime import datetime
import strawberry

from app.models.tag import Tag as TagModel


@strawberry.type
class TagType:
    """標籤 GraphQL 類型"""
    id: strawberry.ID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, tag: TagModel) -> "TagType":
        """從 SQLAlchemy 模型轉換為 GraphQL 類型"""
        return cls(
            id=strawberry.ID(str(tag.id)),
            name=tag.name,
            slug=tag.slug,
            created_at=tag.created_at,
            updated_at=tag.updated_at
        )