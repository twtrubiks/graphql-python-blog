"""
用戶相關 Mutations

提供用戶個人資料更新功能。
"""

import strawberry
from typing import Optional
from sqlalchemy import select
from strawberry.types import Info

from app.models.user import User
from app.graphql.types.user import UserType
from app.core.auth import require_auth


@strawberry.input
class UpdateUserInput:
    """更新用戶資料的輸入類型"""
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


async def update_me(
    info: Info,
    input: UpdateUserInput
) -> UserType:
    """
    更新當前認證用戶的個人資料

    Args:
        info: GraphQL context
        input: 要更新的欄位

    Returns:
        更新後的用戶資料

    Raises:
        ValueError: 如果 username 已被使用
    """
    db_session = info.context.get("db_session")
    current_user = await require_auth(info)

    # 獲取用戶
    result = await db_session.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one()

    # 檢查 username 唯一性
    if input.username and input.username != user.username:
        if not input.username.strip():
            raise ValueError("Username cannot be empty")

        existing = await db_session.execute(
            select(User).where(User.username == input.username)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Username already taken")
        user.username = input.username.strip()

    # 更新欄位
    if input.full_name is not None:
        user.full_name = input.full_name.strip() if input.full_name else None

    if input.bio is not None:
        user.bio = input.bio.strip() if input.bio else None

    if input.avatar_url is not None:
        user.avatar_url = input.avatar_url.strip() if input.avatar_url else None

    await db_session.commit()
    await db_session.refresh(user)

    return UserType.from_orm(user)
