"""
文章刪除訂閱

當追蹤的用戶刪除文章時，訂閱者會收到通知。
用於即時更新 /following 頁面，移除被刪除的文章。
"""

import strawberry
from typing import AsyncGenerator, List
import asyncio


class PostDeletedEvent:
    """
    文章刪除事件管理器

    結構: {user_id: [queues]}
    - key: 訂閱者的 user_id
    - value: 該用戶的所有訂閱 queue 列表（支援多個裝置/分頁）
    """
    _subscribers: dict[int, list[asyncio.Queue]] = {}

    @classmethod
    def subscribe(cls, user_id: int) -> asyncio.Queue:
        """
        訂閱文章刪除事件

        Args:
            user_id: 訂閱者的用戶 ID

        Returns:
            asyncio.Queue: 用於接收刪除事件的佇列
        """
        if user_id not in cls._subscribers:
            cls._subscribers[user_id] = []

        queue = asyncio.Queue()
        cls._subscribers[user_id].append(queue)
        return queue

    @classmethod
    def unsubscribe(cls, user_id: int, queue: asyncio.Queue):
        """
        取消訂閱

        Args:
            user_id: 訂閱者的用戶 ID
            queue: 要取消的訂閱 queue
        """
        if user_id in cls._subscribers:
            if queue in cls._subscribers[user_id]:
                cls._subscribers[user_id].remove(queue)
            # 如果該用戶沒有任何訂閱了，移除整個 key
            if not cls._subscribers[user_id]:
                del cls._subscribers[user_id]

    @classmethod
    async def publish_to_followers(
        cls,
        follower_ids: List[int],
        post_id: int
    ):
        """
        發布文章刪除事件給追蹤者

        只會推送給：
        1. 在 follower_ids 列表中（追蹤該作者）
        2. 且有訂閱 postDeleted 的用戶

        Args:
            follower_ids: 作者的追蹤者 ID 列表
            post_id: 被刪除的文章 ID
        """
        for follower_id in follower_ids:
            # 檢查該追蹤者是否有訂閱
            if follower_id in cls._subscribers:
                # 推送給該追蹤者的所有訂閱 queue
                for queue in cls._subscribers[follower_id]:
                    await queue.put(post_id)


@strawberry.type
class PostDeletedSubscription:
    @strawberry.subscription
    async def post_deleted(
        self,
        info: strawberry.Info
    ) -> AsyncGenerator[strawberry.ID, None]:
        """
        訂閱追蹤用戶的文章刪除事件

        訂閱者身分來自 WebSocket 連線的認證資訊（connectionParams 中的 JWT），
        不接受客戶端自行指定，避免訂閱他人的動態（IDOR）。

        Yields:
            strawberry.ID: 被刪除的文章 ID
        """
        user_id_int = info.context.user_id
        if user_id_int is None:
            raise Exception("Authentication required")

        queue = PostDeletedEvent.subscribe(user_id_int)

        try:
            while True:
                post_id = await queue.get()
                yield strawberry.ID(str(post_id))
        finally:
            PostDeletedEvent.unsubscribe(user_id_int, queue)
