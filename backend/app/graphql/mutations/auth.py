import re
from typing import Optional

import strawberry
from sqlalchemy import select
from app.models.user import User
from app.services.auth import AuthService
from app.graphql.types.user import UserType


@strawberry.type
class AuthPayload:
    user: UserType
    token: str


def validate_email(email: str) -> bool:
    """驗證 email 格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> Optional[str]:
    """驗證密碼強度，回傳錯誤訊息；符合規則時回傳 None"""
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return "Password must contain at least one number"
    return None


async def register(
    email: str,
    password: str, 
    username: str,
    info: strawberry.Info
) -> AuthPayload:
    """註冊新用戶"""
    # 從 context 獲取 db_session
    db_session = info.context.get("db_session")
    
    # 驗證 email 格式
    if not validate_email(email):
        raise ValueError("Invalid email format")
    
    # 驗證密碼強度
    password_error = validate_password(password)
    if password_error:
        raise ValueError(password_error)
    
    # 檢查 email 是否已存在
    result = await db_session.execute(
        select(User).where(User.email == email)
    )
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")
    
    # 檢查 username 是否已存在
    result = await db_session.execute(
        select(User).where(User.username == username)
    )
    if result.scalar_one_or_none():
        raise ValueError("Username already taken")
    
    # 創建新用戶
    hashed_password = AuthService.get_password_hash(password)
    new_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db_session.add(new_user)
    await db_session.commit()  # id 與 created_at 等伺服器端預設值由 INSERT ... RETURNING 帶回，不必再 refresh
    
    # 生成 JWT token
    token = AuthService.create_access_token(
        data={"sub": str(new_user.id)}
    )
    
    return AuthPayload(
        user=UserType.from_orm(new_user),
        token=token
    )


async def login(
    email: str,
    password: str,
    info: strawberry.Info
) -> AuthPayload:
    """用戶登入"""
    # 從 context 獲取 db_session
    db_session = info.context.get("db_session")
    
    # 查找用戶
    result = await db_session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    
    # 檢查用戶是否存在
    if not user:
        raise ValueError("Invalid email or password")
    
    # 驗證密碼
    if not AuthService.verify_password(password, user.hashed_password):
        raise ValueError("Invalid email or password")
    
    # 檢查用戶是否啟用
    if not user.is_active:
        raise ValueError("User account is disabled")
    
    # 生成 JWT token
    token = AuthService.create_access_token(
        data={"sub": str(user.id)}
    )
    
    return AuthPayload(
        user=UserType.from_orm(user),
        token=token
    )