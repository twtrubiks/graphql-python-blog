"""
追蹤用戶發文訂閱

當追蹤的用戶發布新文章時，訂閱者會收到即時通知。
與全域的 postPublished 不同，這個訂閱只會推送給追蹤該作者的用戶。

使用場景：
- 全站通知：登入用戶在任何頁面都能收到追蹤用戶的發文通知
- 追蹤動態頁面：即時更新追蹤用戶的文章列表
"""

import strawberry
from typing import AsyncGenerator, List
import asyncio

from app.graphql.types.post import PostType


class FollowedUserPostEvent:
    """
    追蹤用戶發文事件管理器

    結構: {user_id: [queues]}
    - key: 訂閱者的 user_id
    - value: 該用戶的所有訂閱 queue 列表（支援多個裝置/分頁）
    """
    _subscribers: dict[int, list[asyncio.Queue]] = {}

    @classmethod
    def subscribe(cls, user_id: int) -> asyncio.Queue:
        """
        訂閱追蹤用戶的發文事件

        Args:
            user_id: 訂閱者的用戶 ID

        Returns:
            asyncio.Queue: 用於接收新文章的佇列
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
        post: PostType
    ):
        """
        發布文章給追蹤者

        只會推送給：
        1. 在 follower_ids 列表中（追蹤該作者）
        2. 且有訂閱 followedUserPosted 的用戶

        Args:
            follower_ids: 作者的追蹤者 ID 列表
            post: 新發布的文章
        """
        for follower_id in follower_ids:
            # 檢查該追蹤者是否有訂閱
            if follower_id in cls._subscribers:
                # 推送給該追蹤者的所有訂閱 queue
                for queue in cls._subscribers[follower_id]:
                    await queue.put(post)


@strawberry.type
class FollowedUserPostSubscription:
    @strawberry.subscription
    async def followed_user_posted(
        self,
        info: strawberry.Info
    ) -> AsyncGenerator[PostType, None]:
        """
        訂閱追蹤用戶的新文章發布

        訂閱者身分來自 WebSocket 連線的認證資訊（connectionParams 中的 JWT），
        不接受客戶端自行指定，避免訂閱他人的動態（IDOR）。

        Yields:
            PostType: 追蹤用戶發布的新文章
        """
        user_id_int = info.context.user_id
        if user_id_int is None:
            raise Exception("Authentication required")

        queue = FollowedUserPostEvent.subscribe(user_id_int)

        try:
            while True:
                post = await queue.get()
                yield post
        finally:
            FollowedUserPostEvent.unsubscribe(user_id_int, queue)
