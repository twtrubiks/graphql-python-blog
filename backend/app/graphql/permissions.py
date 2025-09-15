"""
GraphQL 權限控制模組

使用 Strawberry 的 BasePermission 實作 field-level 權限控制
"""
from typing import Any
from strawberry.permission import BasePermission
from strawberry.types import Info
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
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


class IsSuperuser(BasePermission):
    """
    要求用戶必須是超級用戶
    """
    message = "User must be a superuser"

    async def has_permission(
        self, source: Any, info: Info, **kwargs
    ) -> bool:
        """檢查用戶是否為超級用戶"""
        user = await get_current_user(info)
        return user is not None and user.is_superuser


class IsOwner(BasePermission):
    """
    要求用戶必須是資源的擁有者
    用於更新、刪除等操作
    """
    message = "You don't have permission to perform this action"

    async def has_permission(
        self, source: Any, info: Info, **kwargs
    ) -> bool:
        """檢查用戶是否為資源擁有者"""
        user = await get_current_user(info)
        if user is None:
            return False

        # 從 kwargs 中獲取資源 ID
        resource_id = kwargs.get("id")
        if not resource_id:
            return False

        db_session: AsyncSession = info.context.get("db_session")

        # 根據操作類型判斷資源類型
        # 這裡簡化處理，實際應用中可能需要更複雜的邏輯
        field_name = info.field_name

        if "post" in field_name.lower():
            # 檢查文章擁有者
            result = await db_session.execute(
                select(Post).where(Post.id == int(resource_id))
            )
            post = result.scalar_one_or_none()
            return post is not None and post.author_id == user.id

        # 如果是用戶相關操作，檢查是否為本人
        if "user" in field_name.lower():
            return int(resource_id) == user.id

        return False


class IsOwnerOrReadOnly(BasePermission):
    """
    擁有者可以執行所有操作，其他人只能讀取
    """
    message = "You can only modify your own content"

    async def has_permission(
        self, source: Any, info: Info, **kwargs
    ) -> bool:
        """檢查是否為擁有者或只是讀取操作"""
        # 如果是查詢（Query），允許所有人存取
        if info.operation.operation == "query":
            return True

        # 如果是變更（Mutation），檢查是否為擁有者
        user = await get_current_user(info)
        if user is None:
            return False

        # 檢查資源擁有權
        resource_id = kwargs.get("id")
        if not resource_id:
            # 如果是創建新資源，需要登入即可
            return True

        db_session: AsyncSession = info.context.get("db_session")
        field_name = info.field_name

        if "post" in field_name.lower():
            result = await db_session.execute(
                select(Post).where(Post.id == int(resource_id))
            )
            post = result.scalar_one_or_none()
            return post is not None and post.author_id == user.id

        return False


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

        # 檢查是否為資源擁有者
        # 對於 UserType 的欄位，source 就是 User 物件
        if hasattr(source, 'id'):
            # 如果 source 是 UserType，檢查是否為本人
            source_id = int(source.id) if hasattr(source, 'id') else None
            if source_id and source_id == user.id:
                return True

        return False


class CanManageUsers(BasePermission):
    """
    只有超級用戶可以管理其他用戶
    用於用戶列表、禁用用戶等操作
    """
    message = "Only superusers can manage users"

    async def has_permission(
        self, source: Any, info: Info, **kwargs
    ) -> bool:
        """檢查是否有管理用戶的權限"""
        user = await get_current_user(info)
        return user is not None and user.is_superuser