"""
測試 PostDeletedEvent Subscription

文章刪除通知功能測試：
- 訂閱者收到追蹤用戶刪除文章的通知
- 訂閱者不會收到未追蹤用戶刪除文章的通知
- 多個追蹤者同時收到通知
- 訂閱清理機制
"""

import pytest
import asyncio
from app.graphql.subscriptions.post_deleted import (
    PostDeletedEvent,
    PostDeletedSubscription
)
from tests.utils import FakeSubscriptionInfo


@pytest.mark.asyncio
class TestPostDeletedEvent:
    """測試 PostDeletedEvent 事件管理器"""

    async def test_subscriber_receives_deleted_post_notification(self):
        """
        測試訂閱者收到追蹤用戶刪除文章的通知

        場景：
        - user_id=1 訂閱了 postDeleted
        - user_id=1 追蹤了 author_id=2
        - author_id=2 刪除了文章 (post_id=100)
        - user_id=1 應該收到通知
        """
        # Arrange
        subscriber_user_id = 1
        follower_ids = [subscriber_user_id]  # 作者的追蹤者列表
        deleted_post_id = 100

        # Act: 訂閱
        queue = PostDeletedEvent.subscribe(subscriber_user_id)

        try:
            # Act: 發布刪除事件給追蹤者
            await PostDeletedEvent.publish_to_followers(follower_ids, deleted_post_id)

            # Assert: 收到通知
            received_post_id = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert received_post_id == deleted_post_id
        finally:
            PostDeletedEvent.unsubscribe(subscriber_user_id, queue)

    async def test_subscriber_does_not_receive_unfollowed_user_delete(self):
        """
        測試訂閱者不會收到未追蹤用戶刪除文章的通知

        場景：
        - user_id=1 訂閱了 postDeleted
        - user_id=1 沒有追蹤 author_id=3
        - author_id=3 刪除了文章
        - user_id=1 不應該收到通知
        """
        # Arrange
        subscriber_user_id = 1
        other_user_id = 99  # 另一個追蹤者（不是 subscriber）
        follower_ids = [other_user_id]  # 作者的追蹤者不包含 subscriber
        deleted_post_id = 101

        # Act: 訂閱
        queue = PostDeletedEvent.subscribe(subscriber_user_id)

        try:
            # Act: 發布刪除事件給追蹤者（不包含 subscriber）
            await PostDeletedEvent.publish_to_followers(follower_ids, deleted_post_id)

            # Assert: 不應該收到通知（超時）
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue.get(), timeout=0.5)
        finally:
            PostDeletedEvent.unsubscribe(subscriber_user_id, queue)

    async def test_multiple_followers_receive_delete_notification(self):
        """
        測試多個追蹤者同時收到刪除通知

        場景：
        - user_id=1, 2, 3 都訂閱了 postDeleted
        - 他們都追蹤了 author_id=10
        - author_id=10 刪除了文章
        - 三個用戶都應該收到通知
        """
        # Arrange
        subscriber_ids = [1, 2, 3]
        follower_ids = subscriber_ids  # 都是追蹤者
        deleted_post_id = 102

        # Act: 三個用戶都訂閱
        queues = [
            PostDeletedEvent.subscribe(uid) for uid in subscriber_ids
        ]

        try:
            # Act: 發布刪除事件給追蹤者
            await PostDeletedEvent.publish_to_followers(follower_ids, deleted_post_id)

            # Assert: 所有訂閱者都收到
            for queue in queues:
                received_post_id = await asyncio.wait_for(queue.get(), timeout=1.0)
                assert received_post_id == deleted_post_id
        finally:
            for uid, queue in zip(subscriber_ids, queues):
                PostDeletedEvent.unsubscribe(uid, queue)

    async def test_subscription_cleanup(self):
        """
        測試訂閱清理機制

        確保取消訂閱後：
        - 該用戶不再在訂閱者列表中
        - 不會收到新的通知
        """
        # Arrange
        user_id = 999

        # 確保初始狀態乾淨
        initial_count = len(PostDeletedEvent._subscribers.get(user_id, []))

        # Act: 訂閱
        queue1 = PostDeletedEvent.subscribe(user_id)
        queue2 = PostDeletedEvent.subscribe(user_id)

        # Assert: 訂閱者增加
        assert len(PostDeletedEvent._subscribers.get(user_id, [])) == initial_count + 2

        # Act: 取消訂閱
        PostDeletedEvent.unsubscribe(user_id, queue1)
        assert len(PostDeletedEvent._subscribers.get(user_id, [])) == initial_count + 1

        PostDeletedEvent.unsubscribe(user_id, queue2)

        # Assert: 回到初始狀態或已移除
        assert len(PostDeletedEvent._subscribers.get(user_id, [])) == initial_count

    async def test_unsubscribe_nonexistent_queue_no_error(self):
        """測試取消不存在的訂閱不會報錯"""
        # Arrange
        fake_queue = asyncio.Queue()
        user_id = 888

        # Act & Assert: 不應該報錯
        PostDeletedEvent.unsubscribe(user_id, fake_queue)

    async def test_partial_followers_receive_delete_notification(self):
        """
        測試部分追蹤者收到刪除通知

        場景：
        - user_id=1 訂閱且是追蹤者
        - user_id=2 訂閱但不是追蹤者
        - user_id=3 是追蹤者但沒訂閱
        - 只有 user_id=1 應該收到通知
        """
        # Arrange
        follower_ids = [1, 3]  # 追蹤者列表
        deleted_post_id = 103

        # user_id=1 訂閱且是追蹤者
        queue1 = PostDeletedEvent.subscribe(1)
        # user_id=2 訂閱但不是追蹤者
        queue2 = PostDeletedEvent.subscribe(2)
        # user_id=3 是追蹤者但沒訂閱

        try:
            # Act: 發布刪除事件給追蹤者
            await PostDeletedEvent.publish_to_followers(follower_ids, deleted_post_id)

            # Assert: user_id=1 收到通知
            received = await asyncio.wait_for(queue1.get(), timeout=1.0)
            assert received == deleted_post_id

            # Assert: user_id=2 沒有收到（因為不是追蹤者）
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue2.get(), timeout=0.5)
        finally:
            PostDeletedEvent.unsubscribe(1, queue1)
            PostDeletedEvent.unsubscribe(2, queue2)


@pytest.mark.asyncio
class TestPostDeletedSubscription:
    """測試 GraphQL Subscription resolver"""

    async def test_subscription_resolver_yields_post_id(self):
        """測試 GraphQL subscription resolver 返回被刪除的文章 ID"""
        subscription = PostDeletedSubscription()

        user_id = 50
        follower_ids = [user_id]
        deleted_post_id = 104

        # 開始訂閱（訂閱者身分來自已認證的 context，而非客戶端參數）
        subscription_gen = subscription.post_deleted(
            info=FakeSubscriptionInfo(user_id=user_id)
        )

        # 在延遲後發布刪除事件
        async def publish_after_delay():
            await asyncio.sleep(0.1)
            await PostDeletedEvent.publish_to_followers(follower_ids, deleted_post_id)

        publish_task = asyncio.create_task(publish_after_delay())

        # 從 subscription 獲取被刪除的文章 ID
        received_post_id = await anext(subscription_gen)
        assert str(received_post_id) == str(deleted_post_id)

        # 清理
        await publish_task
        await subscription_gen.aclose()

    async def test_subscription_resolver_returns_string_id(self):
        """測試 subscription resolver 返回可轉換為字串的 ID"""
        subscription = PostDeletedSubscription()

        user_id = 51
        follower_ids = [user_id]
        deleted_post_id = 105

        subscription_gen = subscription.post_deleted(
            info=FakeSubscriptionInfo(user_id=user_id)
        )

        async def publish_after_delay():
            await asyncio.sleep(0.1)
            await PostDeletedEvent.publish_to_followers(follower_ids, deleted_post_id)

        publish_task = asyncio.create_task(publish_after_delay())

        received_post_id = await anext(subscription_gen)

        # 驗證返回的 ID 可以正確轉換為字串並匹配
        assert str(received_post_id) == str(deleted_post_id)

        await publish_task
        await subscription_gen.aclose()

    async def test_subscription_requires_authentication(self):
        """未認證（context.user_id 為 None）時應拒絕訂閱"""
        subscription = PostDeletedSubscription()

        subscription_gen = subscription.post_deleted(
            info=FakeSubscriptionInfo(user_id=None)
        )

        with pytest.raises(Exception, match="Authentication required"):
            await anext(subscription_gen)
