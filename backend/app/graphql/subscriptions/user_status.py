import strawberry
from typing import AsyncGenerator
import asyncio
from enum import Enum
from datetime import datetime


@strawberry.enum
class UserStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@strawberry.type
class UserStatusChange:
    user_id: strawberry.ID
    username: str
    status: UserStatus
    timestamp: datetime


@strawberry.type
class OnlineUserInfo:
    """在線用戶資訊，用於初始狀態查詢"""
    user_id: strawberry.ID
    username: str


class UserStatusEvent:
    """用戶狀態事件管理器"""
    _subscribers: list[asyncio.Queue] = []
    _user_status: dict[str, UserStatus] = {}
    _user_connections: dict[str, int] = {}  # 追蹤每個用戶的連線數
    _user_info: dict[str, str] = {}  # 快取 user_id -> username

    @classmethod
    def subscribe(cls) -> asyncio.Queue:
        """訂閱用戶狀態變更"""
        queue = asyncio.Queue()
        cls._subscribers.append(queue)
        return queue

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue):
        """取消訂閱"""
        if queue in cls._subscribers:
            cls._subscribers.remove(queue)

    @classmethod
    async def user_connected(cls, user_id: str, username: str):
        """用戶連線（subscription 開始時調用）"""
        cls._user_info[user_id] = username
        prev_count = cls._user_connections.get(user_id, 0)
        cls._user_connections[user_id] = prev_count + 1

        # 只有從 0 -> 1 時才發送 ONLINE 狀態
        if prev_count == 0:
            await cls.publish_status_change(user_id, username, UserStatus.ONLINE)

    @classmethod
    async def user_disconnected(cls, user_id: str):
        """用戶斷線（subscription 結束時調用）"""
        username = cls._user_info.get(user_id, "Unknown")
        prev_count = cls._user_connections.get(user_id, 0)

        if prev_count > 0:
            cls._user_connections[user_id] = prev_count - 1

            # 只有從 1 -> 0 時才發送 OFFLINE 狀態
            if prev_count == 1:
                await cls.publish_status_change(user_id, username, UserStatus.OFFLINE)

    @classmethod
    async def publish_status_change(cls, user_id: str, username: str, status: UserStatus):
        """發布用戶狀態變更"""
        cls._user_status[user_id] = status

        status_change = UserStatusChange(
            user_id=strawberry.ID(user_id),
            username=username,
            status=status,
            timestamp=datetime.now()
        )

        for queue in cls._subscribers:
            await queue.put(status_change)

    @classmethod
    def get_user_status(cls, user_id: str) -> UserStatus:
        """獲取用戶當前狀態"""
        return cls._user_status.get(user_id, UserStatus.OFFLINE)

    @classmethod
    def get_online_users(cls) -> list[str]:
        """獲取所有在線用戶 ID"""
        return [uid for uid, status in cls._user_status.items()
                if status == UserStatus.ONLINE]


@strawberry.type
class UserStatusSubscription:
    @strawberry.subscription
    async def user_status_changed(
        self,
        user_id: strawberry.ID,
        username: str
    ) -> AsyncGenerator[UserStatusChange, None]:
        """
        訂閱用戶狀態變更

        Args:
            user_id: 當前用戶的 ID
            username: 當前用戶的用戶名
        """
        user_id_str = str(user_id)

        # 先訂閱，再通知上線（確保自己也能收到上線事件）
        queue = UserStatusEvent.subscribe()

        # 通知用戶上線
        await UserStatusEvent.user_connected(user_id_str, username)

        try:
            while True:
                status_change = await queue.get()
                yield status_change
        finally:
            UserStatusEvent.unsubscribe(queue)
            # 通知用戶離線
            await UserStatusEvent.user_disconnected(user_id_str)