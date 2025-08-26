import strawberry
from typing import Optional
from strawberry.types import Info

from app.core.auth import get_current_user, require_auth
from app.graphql.types.user import UserType


@strawberry.type
class ProtectedData:
    message: str
    user_id: str = strawberry.field(name="userId")


async def me(info: Info) -> Optional[UserType]:
    """取得當前認證用戶的資訊"""
    user = await get_current_user(info)
    if not user:
        return None
    return UserType.from_orm(user)


async def protected_data(info: Info) -> ProtectedData:
    """需要認證才能訪問的受保護資料"""
    user = await require_auth(info)
    return ProtectedData(
        message="This is protected data",
        user_id=str(user.id)
    )