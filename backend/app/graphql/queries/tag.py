"""Tag queries"""

import strawberry
from typing import List
from strawberry.types import Info

from app.graphql.types.tag import TagType
from app.services.tag import TagService


@strawberry.type
class TagQuery:
    """標籤相關查詢"""

    @strawberry.field
    async def tags(self, info: Info) -> List[TagType]:
        """取得所有可用標籤"""
        session = info.context["db_session"]
        tags = await TagService.get_all_tags(session)
        return [TagType.from_model(tag) for tag in tags]
