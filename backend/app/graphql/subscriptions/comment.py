import strawberry
from typing import AsyncGenerator
import asyncio

from app.graphql.types.comment import Comment


class CommentEvent:
    """評論事件管理器"""
    _subscribers: dict[str, list[asyncio.Queue]] = {}
    
    @classmethod
    def subscribe(cls, post_id: str) -> asyncio.Queue:
        """訂閱特定文章的評論"""
        if post_id not in cls._subscribers:
            cls._subscribers[post_id] = []
        
        queue = asyncio.Queue()
        cls._subscribers[post_id].append(queue)
        return queue
    
    @classmethod
    def unsubscribe(cls, post_id: str, queue: asyncio.Queue):
        """取消訂閱"""
        if post_id in cls._subscribers:
            if queue in cls._subscribers[post_id]:
                cls._subscribers[post_id].remove(queue)
            if not cls._subscribers[post_id]:
                del cls._subscribers[post_id]
    
    @classmethod
    async def publish(cls, post_id: str, comment: Comment):
        """發布新評論事件"""
        if post_id in cls._subscribers:
            for queue in cls._subscribers[post_id]:
                await queue.put(comment)


@strawberry.type
class CommentSubscription:
    @strawberry.subscription
    async def comment_added(self, post_id: strawberry.ID) -> AsyncGenerator[Comment, None]:
        """訂閱特定文章的新評論"""
        post_id_str = str(post_id)
        queue = CommentEvent.subscribe(post_id_str)
        
        try:
            while True:
                comment = await queue.get()
                yield comment
        finally:
            CommentEvent.unsubscribe(post_id_str, queue)