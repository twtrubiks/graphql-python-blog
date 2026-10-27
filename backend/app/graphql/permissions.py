"""
GraphQL 權限控制模組

使用 Strawberry 的 BasePermission 實作 field-level 權限控制
"""
from typing import Any
from strawberry.permission import BasePermission
from strawberry.types import Info

from app.core.auth import get_current_user


class IsAuthenticated(BasePermission):
    """
    要求用戶必須已認證（登入）
    """
    message = "Authentication required"

    async def has_permission(
        self, source: Any, info: Info, **kwargs
    ) -> bool:
        """檢查用戶是否已認證"""
        user = await get_current_user(info)
        return user is not None


class IsOwnerOrSuperuser(BasePermission):
    """
    擁有者或超級用戶可以存取
    用於敏感資料如 email
    """
    message = "You don't have permission to view this field"

    async def has_permission(
        self, source: Any, info: Info, **kwargs
    ) -> bool:
        """檢查是否為擁有者或超級用戶"""
        user = await get_current_user(info)
        if user is None:
            return False

        # 如果是超級用戶，允許存取
        if user.is_superuser:
            return True

        # 檢查是否為資源擁有者：對於 UserType 的欄位，source 就是該 UserType
        source_id = getattr(source, "id", None)
        return source_id is not None and int(source_id) == user.id