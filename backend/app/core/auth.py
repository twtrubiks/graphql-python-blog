from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info

from app.models.user import User
from app.services.auth import AuthService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    info: Info,
    token: Optional[str] = None
) -> Optional[User]:
    """
    從 JWT token 獲取當前用戶
    可以從 Authorization header 或直接傳入 token
    """
    db_session = info.context.get("db_session")
    request = info.context.get("request")
    
    # 嘗試從 request headers 獲取 token
    if not token and request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        return None
    
    # 驗證 token
    payload = AuthService.verify_token(token)
    if not payload:
        return None
    
    # 從資料庫獲取用戶
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db_session.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        return None
    
    return user


async def require_auth(info: Info) -> User:
    """
    要求認證的 decorator/helper function
    如果用戶未認證，拋出錯誤
    """
    user = await get_current_user(info)
    if not user:
        raise ValueError("Authentication required")
    return user


async def get_current_user_optional(info: Info) -> Optional[User]:
    """
    獲取當前用戶（如果已認證）
    如果未認證，返回 None 而不拋出錯誤
    """
    return await get_current_user(info)