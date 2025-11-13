"""
🎓 教學重點：GraphQL Subscription（訂閱）實作即時通知

## 什麼是 GraphQL Subscription？
Subscription 是 GraphQL 的第三種操作類型（另外兩種是 Query 和 Mutation）：
- Query: 讀取資料（一次性）
- Mutation: 修改資料（一次性）
- Subscription: 訂閱資料變更（持續推送）✨

## 使用場景
- 💬 即時聊天訊息
- 📝 新評論通知
- 👥 使用者上線/離線狀態
- 🔔 系統通知推送
- 📊 即時資料更新（股票、遊戲分數等）

## 技術架構
```
客戶端                           伺服器
  |                               |
  |------ WebSocket 連接 -------> |
  |                               |
  |-- subscription query -------> | 註冊訂閱
  |                               |
  |                               | (等待事件發生...)
  |                               |
  | <----- 新評論事件 ----------- | 有新評論！
  | <----- 新評論事件 ----------- | 又有新評論！
  |                               |
```

## 實作方式
1. **發布-訂閱模式（Pub-Sub）**：
   - Subscribe: 客戶端訂閱特定主題（如 "post:123 的評論"）
   - Publish: 後端發布事件（如 "post:123 新增了評論"）
   - 訂閱者自動收到通知

2. **WebSocket 連線**：
   - 持久化連接（不像 HTTP 請求完就斷）
   - 雙向通訊（伺服器可主動推送）

## 學習建議
1. 從 test_new_comment_notification 開始，了解基本訂閱流程
2. 觀察 test_only_subscribed_post_comments 學習訂閱隔離
3. test_multiple_users_subscription 展示多用戶廣播

## 相關檔案
- app/graphql/subscriptions/comment.py - CommentEvent 實作
- tests/graphql/test_subscription_websocket.py - WebSocket 連線測試
- docs/graphql-examples.md - Subscription 使用範例

## 前端使用範例
```javascript
// 訂閱新評論
subscription {
  commentAdded(postId: "123") {
    id
    content
    author {
      username
    }
  }
}
```
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.graphql.subscriptions.comment import CommentEvent, CommentSubscription
from app.graphql.types.comment import Comment


@pytest.mark.asyncio
class TestCommentSubscription:
    """
    測試評論即時通知功能

    🎯 測試重點：
    1. Pub-Sub 機制是否正常運作
    2. 訂閱隔離（只收到訂閱文章的評論）
    3. 多用戶同時訂閱
    4. 訂閱清理和記憶體洩漏防範
    """

    async def test_new_comment_notification(self):
        """
        測試新評論時發送通知

        📝 測試流程（Pub-Sub 基本循環）：
        1. Subscribe（訂閱）：註冊訂閱 post_id="1" 的評論
        2. Publish（發布）：新增一則評論到 post_id="1"
        3. Receive（接收）：訂閱者應該自動收到該評論

        💡 關鍵概念：
        - queue：每個訂閱者有自己的佇列接收訊息
        - publish：觸發事件，所有訂閱該主題的 queue 都會收到
        - asyncio.wait_for：非同步等待訊息（設定超時避免測試卡住）
        """
        # ==================== Arrange ====================
        post_id = "1"

        # 📝 創建測試用的評論資料
        test_comment = Comment(
            id="comment1",
            content="Test comment",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # ==================== Act ====================
        # 📝 Step 1: 訂閱（Subscribe）
        # CommentEvent.subscribe() 會返回一個 asyncio.Queue
        # 這個 queue 會接收所有 post_id="1" 的新評論事件
        queue = CommentEvent.subscribe(post_id)

        # 📝 Step 2: 發布事件（Publish）
        # 當有新評論時，後端會呼叫 publish 觸發事件
        # 所有訂閱 post_id="1" 的 queue 都會收到這則評論
        await CommentEvent.publish(post_id, test_comment)

        # ==================== Assert ====================
        # 📝 Step 3: 接收通知（Receive）
        # queue.get() 會等待並取出一則訊息
        # asyncio.wait_for() 設定 1 秒超時，避免測試永久等待
        received_comment = await asyncio.wait_for(queue.get(), timeout=1.0)

        # 📝 驗證收到的評論與發布的評論相同
        assert received_comment.id == test_comment.id
        assert received_comment.content == test_comment.content

        # 📝 清理資源（重要！）
        # 取消訂閱避免記憶體洩漏
        CommentEvent.unsubscribe(post_id, queue)
    
    async def test_only_subscribed_post_comments(self):
        """
        測試只接收訂閱文章的評論（訂閱隔離）

        🎯 學習重點：
        訂閱應該有「隔離性」- 只收到訂閱主題的訊息

        📝 測試場景：
        - 有兩篇文章：post1 和 post2
        - 用戶只訂閱 post1 的評論
        - 當 post1 和 post2 都有新評論時
        - 用戶應該只收到 post1 的評論，不會收到 post2 的

        💡 實務應用：
        這確保了即時通知的正確性，避免：
        - 用戶收到不相關的通知（隱私問題）
        - 伺服器資源浪費（不必要的推送）
        """
        # ==================== Arrange ====================
        post1_id = "1"
        post2_id = "2"

        # 📝 創建兩個不同文章的評論
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

        # ==================== Act ====================
        # 📝 只訂閱 post1（重點：沒有訂閱 post2）
        queue = CommentEvent.subscribe(post1_id)

        # 📝 發布兩個評論（兩篇文章都有新評論）
        await CommentEvent.publish(post1_id, comment1)  # 這個應該收到
        await CommentEvent.publish(post2_id, comment2)  # 這個不應該收到

        # ==================== Assert ====================
        # 📝 應該只收到 post1 的評論
        received_comment = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received_comment.id == comment1.id

        # 📝 確認 queue 中沒有其他評論（post2 的評論沒有被推送）
        # queue.empty() 確保沒有多餘的訊息
        assert queue.empty(), "Should not receive comment from post2"

        # 📝 清理
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