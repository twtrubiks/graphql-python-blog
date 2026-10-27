from typing import Optional
from strawberry.types import Info
from app.core.auth import get_current_user


async def get_current_user_id(info: Info) -> Optional[int]:
    """
    獲取當前用戶的 ID
    如果用戶未認證，返回 None
    """
    user = await get_current_user(info)
    return user.id if user else None
