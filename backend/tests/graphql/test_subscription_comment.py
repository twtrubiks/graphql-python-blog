import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.graphql.subscriptions.comment import CommentEvent, CommentSubscription
from app.graphql.types.comment import Comment


@pytest.mark.asyncio
class TestCommentSubscription:
    """測試評論即時通知功能"""
    
    async def test_new_comment_notification(self):
        """測試新評論時發送通知"""
        post_id = "1"
        
        # 創建測試用的評論
        test_comment = Comment(
            id="comment1",
            content="Test comment",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 訂閱評論
        queue = CommentEvent.subscribe(post_id)
        
        # 發布新評論
        await CommentEvent.publish(post_id, test_comment)
        
        # 檢查是否收到通知
        received_comment = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received_comment.id == test_comment.id
        assert received_comment.content == test_comment.content
        
        # 清理
        CommentEvent.unsubscribe(post_id, queue)
    
    async def test_only_subscribed_post_comments(self):
        """測試只接收訂閱文章的評論"""
        post1_id = "1"
        post2_id = "2"
        
        # 創建兩個不同文章的評論
        comment1 = Comment(
            id="comment1",
            content="Comment for post 1",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        comment2 = Comment(
            id="comment2",
            content="Comment for post 2",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 只訂閱 post1
        queue = CommentEvent.subscribe(post1_id)
        
        # 發布兩個評論
        await CommentEvent.publish(post1_id, comment1)
        await CommentEvent.publish(post2_id, comment2)
        
        # 應該只收到 post1 的評論
        received_comment = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received_comment.id == comment1.id
        
        # 確認 queue 中沒有其他評論
        assert queue.empty()
        
        # 清理
        CommentEvent.unsubscribe(post1_id, queue)
    
    async def test_multiple_users_subscription(self):
        """測試多用戶同時訂閱"""
        post_id = "1"
        
        # 創建測試評論
        test_comment = Comment(
            id="comment1",
            content="Shared comment",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 多個用戶訂閱同一文章
        queue1 = CommentEvent.subscribe(post_id)
        queue2 = CommentEvent.subscribe(post_id)
        queue3 = CommentEvent.subscribe(post_id)
        
        # 發布評論
        await CommentEvent.publish(post_id, test_comment)
        
        # 所有訂閱者都應該收到評論
        received1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        received2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
        received3 = await asyncio.wait_for(queue3.get(), timeout=1.0)
        
        assert received1.id == test_comment.id
        assert received2.id == test_comment.id
        assert received3.id == test_comment.id
        
        # 清理
        CommentEvent.unsubscribe(post_id, queue1)
        CommentEvent.unsubscribe(post_id, queue2)
        CommentEvent.unsubscribe(post_id, queue3)
    
    async def test_subscription_cleanup(self):
        """測試訂閱清理機制"""
        post_id = "1"
        
        # 訂閱
        queue1 = CommentEvent.subscribe(post_id)
        queue2 = CommentEvent.subscribe(post_id)
        
        # 確認訂閱者存在
        assert post_id in CommentEvent._subscribers
        assert len(CommentEvent._subscribers[post_id]) == 2
        
        # 取消訂閱
        CommentEvent.unsubscribe(post_id, queue1)
        assert len(CommentEvent._subscribers[post_id]) == 1
        
        CommentEvent.unsubscribe(post_id, queue2)
        # 當沒有訂閱者時，應該刪除 post_id 的 key
        assert post_id not in CommentEvent._subscribers
    
    async def test_comment_subscription_resolver(self):
        """測試 GraphQL subscription resolver"""
        subscription = CommentSubscription()
        post_id = "test_post"
        
        # 創建測試評論
        test_comment = Comment(
            id="comment1",
            content="Test comment via resolver",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 開始訂閱
        subscription_gen = subscription.comment_added(post_id)
        
        # 在另一個協程中發布評論
        async def publish_after_delay():
            await asyncio.sleep(0.1)
            await CommentEvent.publish(post_id, test_comment)
        
        # 啟動發布任務
        publish_task = asyncio.create_task(publish_after_delay())
        
        # 從 subscription 獲取評論
        received_comment = await anext(subscription_gen)
        assert received_comment.id == test_comment.id
        assert received_comment.content == test_comment.content
        
        # 清理
        await publish_task
        await subscription_gen.aclose()