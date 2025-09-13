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


async def require_user_id(info: Info) -> int:
    """
    要求認證並返回用戶 ID
    如果用戶未認證，拋出錯誤
    """
    user_id = await get_current_user_id(info)
    if not user_id:
        raise ValueError("Authentication required")
    return user_id