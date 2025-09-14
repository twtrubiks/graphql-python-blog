"""追蹤功能 GraphQL types"""
import strawberry
from typing import Optional
from datetime import datetime

from app.graphql.types.user import UserType


@strawberry.type
class FollowType:
    """追蹤關係類型"""
    id: strawberry.ID
    follower: UserType
    followed: UserType
    created_at: datetime


@strawberry.type
class FollowResponse:
    """追蹤操作響應"""
    success: bool
    message: str
    follow: Optional[FollowType] = None


@strawberry.type
class UnfollowResponse:
    """取消追蹤響應"""
    success: bool
    message: str