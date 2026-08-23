"""
評論相關訂閱

三個事件以「文章 ID」為主題、各自獨立的 in-process pub/sub channel：
- commentAdded   : 新增評論（推送完整 Comment）
- commentUpdated : 編輯評論（推送完整 Comment，前端以 id 覆蓋內容）
- commentDeleted : 刪除評論（只推送 commentId / postId / totalComments）

channel 分開而非共用一個帶 type 欄位的事件，是為了與現有
postPublished / postDeleted 的「一個事件一個 subscription」風格一致。
"""

import strawberry
from typing import AsyncGenerator, Generic, TypeVar
import asyncio

from app.graphql.types.comment import Comment


T = TypeVar("T")


class PostScopedEvent(Generic[T]):
    """
    以 post_id 為主題的事件管理器基底

    每個子類別擁有獨立的 `_subscribers`（由 __init_subclass__ 建立），
    因此不同事件的訂閱者互不干擾。

    結構: {post_id: [queues]}
    """
    _subscribers: dict[str, list[asyncio.Queue]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._subscribers = {}

    @classmethod
    def subscribe(cls, post_id: str) -> asyncio.Queue:
        """訂閱特定文章的事件"""
        if post_id not in cls._subscribers:
            cls._subscribers[post_id] = []

        queue: asyncio.Queue = asyncio.Queue()
        cls._subscribers[post_id].append(queue)
        return queue

    @classmethod
    def unsubscribe(cls, post_id: str, queue: asyncio.Queue):
        """取消訂閱；該文章沒有任何訂閱者時移除整個 key"""
        if post_id in cls._subscribers:
            if queue in cls._subscribers[post_id]:
                cls._subscribers[post_id].remove(queue)
            if not cls._subscribers[post_id]:
                del cls._subscribers[post_id]

    @classmethod
    async def publish(cls, post_id: str, payload: T):
        """發布事件給該文章的所有訂閱者"""
        if post_id in cls._subscribers:
            for queue in cls._subscribers[post_id]:
                await queue.put(payload)


class CommentEvent(PostScopedEvent[Comment]):
    """新評論事件管理器"""


class CommentUpdatedEvent(PostScopedEvent[Comment]):
    """評論編輯事件管理器"""


@strawberry.type
class CommentDeletedPayload:
    """評論刪除事件 payload"""
    comment_id: strawberry.ID
    post_id: strawberry.ID
    # 刪除後該文章剩餘的評論數（伺服器計算的絕對值，前端不自行 -1）
    total_comments: int


class CommentDeletedEvent(PostScopedEvent[CommentDeletedPayload]):
    """評論刪除事件管理器"""


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

    @strawberry.subscription
    async def comment_updated(self, post_id: strawberry.ID) -> AsyncGenerator[Comment, None]:
        """訂閱特定文章的評論編輯"""
        post_id_str = str(post_id)
        queue = CommentUpdatedEvent.subscribe(post_id_str)

        try:
            while True:
                comment = await queue.get()
                yield comment
        finally:
            CommentUpdatedEvent.unsubscribe(post_id_str, queue)

    @strawberry.subscription
    async def comment_deleted(self, post_id: strawberry.ID) -> AsyncGenerator[CommentDeletedPayload, None]:
        """訂閱特定文章的評論刪除"""
        post_id_str = str(post_id)
        queue = CommentDeletedEvent.subscribe(post_id_str)

        try:
            while True:
                payload = await queue.get()
                yield payload
        finally:
            CommentDeletedEvent.unsubscribe(post_id_str, queue)
