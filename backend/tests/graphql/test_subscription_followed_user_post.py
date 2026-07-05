"""
測試 FollowedUserPostEvent Subscription

追蹤用戶發文通知功能測試：
- 訂閱者收到追蹤用戶的新文章
- 訂閱者不會收到未追蹤用戶的文章
- 多個追蹤者同時收到通知
- 訂閱清理機制
"""

import pytest
import asyncio
from datetime import datetime
from app.graphql.subscriptions.followed_user_post import (
    FollowedUserPostEvent,
    FollowedUserPostSubscription
)
from app.graphql.types.post import PostType
from app.models.post import PostStatus
from tests.utils import FakeSubscriptionInfo


@pytest.mark.asyncio
class TestFollowedUserPostEvent:
    """測試 FollowedUserPostEvent 事件管理器"""

    async def test_subscriber_receives_followed_user_post(self):
        """
        測試訂閱者收到追蹤用戶的新文章

        場景：
        - user_id=1 訂閱了 followedUserPosted
        - user_id=1 追蹤了 author_id=2
        - author_id=2 發布新文章
        - user_id=1 應該收到通知
        """
        # Arrange
        subscriber_user_id = 1
        author_user_id = 2
        follower_ids = [subscriber_user_id]  # 作者的追蹤者列表

        test_post = PostType(
            id=100,
            title="追蹤用戶的新文章",
            slug="followed-user-post",
            content="文章內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=author_user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # Act: 訂閱
        queue = FollowedUserPostEvent.subscribe(subscriber_user_id)

        try:
            # Act: 發布給追蹤者
            await FollowedUserPostEvent.publish_to_followers(follower_ids, test_post)

            # Assert: 收到通知
            received_post = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert received_post.id == test_post.id
            assert received_post.title == test_post.title
            assert received_post.author_id == author_user_id
        finally:
            FollowedUserPostEvent.unsubscribe(subscriber_user_id, queue)

    async def test_subscriber_does_not_receive_unfollowed_user_post(self):
        """
        測試訂閱者不會收到未追蹤用戶的文章

        場景：
        - user_id=1 訂閱了 followedUserPosted
        - user_id=1 沒有追蹤 author_id=3
        - author_id=3 發布新文章
        - user_id=1 不應該收到通知
        """
        # Arrange
        subscriber_user_id = 1
        other_user_id = 99  # 另一個追蹤者（不是 subscriber）
        follower_ids = [other_user_id]  # 作者的追蹤者不包含 subscriber

        test_post = PostType(
            id=101,
            title="未追蹤用戶的文章",
            slug="not-followed-post",
            content="內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # Act: 訂閱
        queue = FollowedUserPostEvent.subscribe(subscriber_user_id)

        try:
            # Act: 發布給追蹤者（不包含 subscriber）
            await FollowedUserPostEvent.publish_to_followers(follower_ids, test_post)

            # Assert: 不應該收到通知（超時）
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue.get(), timeout=0.5)
        finally:
            FollowedUserPostEvent.unsubscribe(subscriber_user_id, queue)

    async def test_multiple_followers_receive_notification(self):
        """
        測試多個追蹤者同時收到通知

        場景：
        - user_id=1, 2, 3 都訂閱了 followedUserPosted
        - 他們都追蹤了 author_id=10
        - author_id=10 發布新文章
        - 三個用戶都應該收到通知
        """
        # Arrange
        subscriber_ids = [1, 2, 3]
        follower_ids = subscriber_ids  # 都是追蹤者

        test_post = PostType(
            id=102,
            title="多人追蹤的文章",
            slug="multi-follower-post",
            content="內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=10,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # Act: 三個用戶都訂閱
        queues = [
            FollowedUserPostEvent.subscribe(uid) for uid in subscriber_ids
        ]

        try:
            # Act: 發布給追蹤者
            await FollowedUserPostEvent.publish_to_followers(follower_ids, test_post)

            # Assert: 所有訂閱者都收到
            for queue in queues:
                received_post = await asyncio.wait_for(queue.get(), timeout=1.0)
                assert received_post.id == test_post.id
                assert received_post.title == test_post.title
        finally:
            for uid, queue in zip(subscriber_ids, queues):
                FollowedUserPostEvent.unsubscribe(uid, queue)

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
        initial_count = len(FollowedUserPostEvent._subscribers.get(user_id, []))

        # Act: 訂閱
        queue1 = FollowedUserPostEvent.subscribe(user_id)
        queue2 = FollowedUserPostEvent.subscribe(user_id)

        # Assert: 訂閱者增加
        assert len(FollowedUserPostEvent._subscribers.get(user_id, [])) == initial_count + 2

        # Act: 取消訂閱
        FollowedUserPostEvent.unsubscribe(user_id, queue1)
        assert len(FollowedUserPostEvent._subscribers.get(user_id, [])) == initial_count + 1

        FollowedUserPostEvent.unsubscribe(user_id, queue2)

        # Assert: 回到初始狀態或已移除
        assert len(FollowedUserPostEvent._subscribers.get(user_id, [])) == initial_count

    async def test_unsubscribe_nonexistent_queue_no_error(self):
        """測試取消不存在的訂閱不會報錯"""
        # Arrange
        fake_queue = asyncio.Queue()
        user_id = 888

        # Act & Assert: 不應該報錯
        FollowedUserPostEvent.unsubscribe(user_id, fake_queue)

    async def test_partial_followers_receive_notification(self):
        """
        測試部分追蹤者收到通知

        場景：
        - user_id=1 訂閱且是追蹤者
        - user_id=2 訂閱但不是追蹤者
        - user_id=3 是追蹤者但沒訂閱
        - 只有 user_id=1 應該收到通知
        """
        # Arrange
        follower_ids = [1, 3]  # 追蹤者列表

        test_post = PostType(
            id=103,
            title="部分追蹤測試",
            slug="partial-test",
            content="內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=20,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # user_id=1 訂閱且是追蹤者
        queue1 = FollowedUserPostEvent.subscribe(1)
        # user_id=2 訂閱但不是追蹤者
        queue2 = FollowedUserPostEvent.subscribe(2)
        # user_id=3 是追蹤者但沒訂閱

        try:
            # Act: 發布給追蹤者
            await FollowedUserPostEvent.publish_to_followers(follower_ids, test_post)

            # Assert: user_id=1 收到通知
            received = await asyncio.wait_for(queue1.get(), timeout=1.0)
            assert received.id == test_post.id

            # Assert: user_id=2 沒有收到（因為不是追蹤者）
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue2.get(), timeout=0.5)
        finally:
            FollowedUserPostEvent.unsubscribe(1, queue1)
            FollowedUserPostEvent.unsubscribe(2, queue2)


@pytest.mark.asyncio
class TestFollowedUserPostSubscription:
    """測試 GraphQL Subscription resolver"""

    async def test_subscription_resolver(self):
        """測試 GraphQL subscription resolver"""
        subscription = FollowedUserPostSubscription()

        user_id = 50
        follower_ids = [user_id]

        test_post = PostType(
            id=104,
            title="Resolver 測試",
            slug="resolver-test",
            content="內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=30,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # 開始訂閱（訂閱者身分來自已認證的 context，而非客戶端參數）
        subscription_gen = subscription.followed_user_posted(
            info=FakeSubscriptionInfo(user_id=user_id)
        )

        # 在延遲後發布文章
        async def publish_after_delay():
            await asyncio.sleep(0.1)
            await FollowedUserPostEvent.publish_to_followers(follower_ids, test_post)

        publish_task = asyncio.create_task(publish_after_delay())

        # 從 subscription 獲取文章
        received_post = await anext(subscription_gen)
        assert received_post.id == test_post.id
        assert received_post.title == test_post.title

        # 清理
        await publish_task
        await subscription_gen.aclose()

    async def test_subscription_requires_authentication(self):
        """未認證（context.user_id 為 None）時應拒絕訂閱"""
        subscription = FollowedUserPostSubscription()

        subscription_gen = subscription.followed_user_posted(
            info=FakeSubscriptionInfo(user_id=None)
        )

        with pytest.raises(Exception, match="Authentication required"):
            await anext(subscription_gen)
