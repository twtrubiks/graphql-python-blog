import strawberry
from typing import AsyncGenerator
import asyncio
from datetime import datetime

from app.graphql.types.post import PostType


class PostEvent:
    """文章事件管理器"""
    _subscribers: list[asyncio.Queue] = []

    @classmethod
    def subscribe(cls) -> asyncio.Queue:
        """訂閱文章發布事件"""
        queue = asyncio.Queue()
        cls._subscribers.append(queue)
        return queue

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue):
        """取消訂閱"""
        if queue in cls._subscribers:
            cls._subscribers.remove(queue)

    @classmethod
    async def publish_post(cls, post: PostType):
        """發布新文章事件"""
        # 發送給所有訂閱者
        for queue in cls._subscribers:
            await queue.put(post)


@strawberry.type
class PostSubscription:
    @strawberry.subscription
    async def post_published(self) -> AsyncGenerator[PostType, None]:
        """訂閱新文章發布事件"""
        queue = PostEvent.subscribe()

        try:
            while True:
                post = await queue.get()
                yield post
        finally:
            PostEvent.unsubscribe(queue)