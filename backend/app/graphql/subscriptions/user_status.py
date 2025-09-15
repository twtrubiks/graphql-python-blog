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


class UserStatusEvent:
    """用戶狀態事件管理器"""
    _subscribers: list[asyncio.Queue] = []
    _user_status: dict[str, UserStatus] = {}
    
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


@strawberry.type
class UserStatusSubscription:
    @strawberry.subscription
    async def user_status_changed(self) -> AsyncGenerator[UserStatusChange, None]:
        """訂閱用戶狀態變更"""
        queue = UserStatusEvent.subscribe()
        
        try:
            while True:
                status_change = await queue.get()
                yield status_change
        finally:
            UserStatusEvent.unsubscribe(queue)