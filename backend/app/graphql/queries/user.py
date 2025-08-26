from typing import Optional, List
from sqlalchemy import select
from strawberry.types import Info
from app.models.user import User
from app.graphql.types.user import UserType


async def get_user(
    info: Info,
    id: Optional[int] = None,
    username: Optional[str] = None
) -> Optional[UserType]:
    """
    查詢單一用戶
    
    Args:
        info: Strawberry Info object containing request context
        id: 用戶 ID
        username: 用戶名稱
    
    Returns:
        UserType 或 None
    """
    if not id and not username:
        return None
    
    db = info.context["db_session"]
    query = select(User)
    
    if id:
        query = query.where(User.id == id)
    elif username:
        query = query.where(User.username == username)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    return UserType.from_orm(user)


async def get_users(
    info: Info,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    is_active: Optional[bool] = None
) -> List[UserType]:
    """
    查詢用戶列表
    
    Args:
        info: Strawberry Info object containing request context
        page: 頁數（從 1 開始）
        limit: 每頁數量
        is_active: 過濾活躍狀態
    
    Returns:
        用戶列表
    """
    db = info.context["db_session"]
    query = select(User)
    
    # 過濾活躍狀態
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # 預設按創建時間降序排列（最新的在前）
    query = query.order_by(User.created_at.desc())
    
    # 分頁處理
    if page and limit:
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
    elif limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserType.from_orm(user) for user in users]