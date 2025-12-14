"""
🎓 教學重點：GraphQL Subscription - 文章發布即時通知

## 什麼是 postPublished Subscription？
當有新文章發布時，所有訂閱的客戶端都會即時收到通知。
這與 commentAdded 訂閱不同：
- commentAdded: 訂閱特定文章的評論（需要 postId 參數）
- postPublished: 訂閱所有新發布的文章（全域訂閱）

## 使用場景
- 🏠 首頁即時顯示新文章
- 🔔 新文章通知系統
- 📱 推送通知觸發

## 技術架構
```
訂閱者 A (首頁)                    伺服器
訂閱者 B (文章列表)                  |
    |                               |
    |------ WebSocket 連接 -------> |
    |                               |
    |-- postPublished subscription ->| 註冊全域訂閱
    |                               |
    |                               | (作者發布文章...)
    |                               |
    | <----- 新文章資料 ----------- | 廣播給所有訂閱者
    |                               |
```

## 相關檔案
- app/graphql/subscriptions/post.py - PostEvent 實作
- app/graphql/mutations/post.py - publishPost mutation (觸發事件)
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
from app.graphql.subscriptions.post import PostEvent, PostSubscription
from app.graphql.types.post import PostType
from app.models.post import PostStatus


@pytest.mark.asyncio
class TestPostPublishedSubscription:
    """
    測試文章發布即時通知功能

    🎯 測試重點：
    1. 單一訂閱者能收到新發布的文章
    2. 多個訂閱者同時收到廣播
    3. 訂閱清理機制正常運作
    """

    async def test_post_published_notification(self):
        """
        測試新文章發布時發送通知

        📝 測試流程：
        1. Subscribe（訂閱）：註冊全域文章發布訂閱
        2. Publish（發布）：發布一篇新文章
        3. Receive（接收）：訂閱者應該收到該文章

        💡 與 CommentEvent 不同：
        - PostEvent 是全域訂閱，不需要指定 post_id
        - 所有訂閱者都會收到所有新發布的文章
        """
        # ==================== Arrange ====================
        # 📝 創建測試用的文章資料
        test_post = PostType(
            id=1,
            title="測試文章標題",
            slug="test-post-slug",
            content="這是測試文章的內容",
            _excerpt="測試摘要",
            status=PostStatus.PUBLISHED,
            author_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # ==================== Act ====================
        # 📝 Step 1: 訂閱（Subscribe）
        # PostEvent.subscribe() 返回一個 asyncio.Queue
        queue = PostEvent.subscribe()

        try:
            # 📝 Step 2: 發布事件（Publish）
            # 當文章發布時，後端會呼叫 publish_post 觸發事件
            await PostEvent.publish_post(test_post)

            # ==================== Assert ====================
            # 📝 Step 3: 接收通知（Receive）
            received_post = await asyncio.wait_for(queue.get(), timeout=1.0)

            # 📝 驗證收到的文章與發布的文章相同
            assert received_post.id == test_post.id
            assert received_post.title == test_post.title
            assert received_post.slug == test_post.slug
        finally:
            # 📝 清理資源
            PostEvent.unsubscribe(queue)

    async def test_multiple_subscribers_receive_broadcast(self):
        """
        測試多個訂閱者同時收到廣播

        📝 測試場景：
        - 三個用戶同時在首頁（都訂閱了 postPublished）
        - 有人發布新文章
        - 三個用戶都應該即時收到新文章資訊

        💡 這是「廣播」模式的核心特性
        """
        # ==================== Arrange ====================
        test_post = PostType(
            id=2,
            title="廣播測試文章",
            slug="broadcast-test",
            content="測試內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # 📝 三個訂閱者（模擬三個用戶在首頁）
        queue1 = PostEvent.subscribe()
        queue2 = PostEvent.subscribe()
        queue3 = PostEvent.subscribe()

        try:
            # ==================== Act ====================
            # 📝 發布一篇文章
            await PostEvent.publish_post(test_post)

            # ==================== Assert ====================
            # 📝 所有訂閱者都應該收到
            received1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
            received2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
            received3 = await asyncio.wait_for(queue3.get(), timeout=1.0)

            # 📝 驗證三個訂閱者收到的內容相同
            assert received1.id == test_post.id
            assert received2.id == test_post.id
            assert received3.id == test_post.id

            assert received1.title == test_post.title
            assert received2.title == test_post.title
            assert received3.title == test_post.title
        finally:
            # 📝 清理
            PostEvent.unsubscribe(queue1)
            PostEvent.unsubscribe(queue2)
            PostEvent.unsubscribe(queue3)

    async def test_subscription_cleanup(self):
        """
        測試訂閱清理機制

        📝 為什麼需要清理？
        - 避免記憶體洩漏
        - 確保離線用戶不再收到訊息
        - 維護 _subscribers 列表的正確性
        """
        # ==================== Arrange ====================
        initial_count = len(PostEvent._subscribers)

        # 📝 新增訂閱
        queue1 = PostEvent.subscribe()
        queue2 = PostEvent.subscribe()

        # 📝 確認訂閱者增加
        assert len(PostEvent._subscribers) == initial_count + 2

        # ==================== Act ====================
        # 📝 取消訂閱
        PostEvent.unsubscribe(queue1)
        assert len(PostEvent._subscribers) == initial_count + 1

        PostEvent.unsubscribe(queue2)

        # ==================== Assert ====================
        # 📝 確認回到初始狀態
        assert len(PostEvent._subscribers) == initial_count

    async def test_post_subscription_resolver(self):
        """
        測試 GraphQL subscription resolver

        📝 這測試實際的 GraphQL resolver 邏輯
        確保 PostSubscription.post_published() 正確運作
        """
        subscription = PostSubscription()

        # 📝 創建測試文章
        test_post = PostType(
            id=3,
            title="Resolver 測試文章",
            slug="resolver-test",
            content="測試內容",
            _excerpt="摘要",
            status=PostStatus.PUBLISHED,
            author_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=datetime.now(),
        )

        # 📝 開始訂閱
        subscription_gen = subscription.post_published()

        # 📝 在延遲後發布文章
        async def publish_after_delay():
            await asyncio.sleep(0.1)
            await PostEvent.publish_post(test_post)

        # 📝 啟動發布任務
        publish_task = asyncio.create_task(publish_after_delay())

        # 📝 從 subscription 獲取文章
        received_post = await anext(subscription_gen)
        assert received_post.id == test_post.id
        assert received_post.title == test_post.title

        # 📝 清理
        await publish_task
        await subscription_gen.aclose()

    async def test_unsubscribe_nonexistent_queue(self):
        """
        測試取消不存在的訂閱不會報錯

        📝 防禦性編程：確保重複取消訂閱不會崩潰
        """
        # 📝 創建一個未訂閱的 queue
        fake_queue = asyncio.Queue()

        # 📝 取消訂閱不應該報錯
        # 這不應該拋出任何異常
        PostEvent.unsubscribe(fake_queue)


@pytest.mark.asyncio
class TestPostPublishedIntegration:
    """
    整合測試：確保 publishPost mutation 正確觸發 subscription

    注意：這些測試需要實際的資料庫連線和 GraphQL schema
    """

    async def test_publish_post_triggers_subscription(
        self, authenticated_client, test_session, test_user
    ):
        """
        測試發布文章時觸發 subscription 事件

        📝 完整流程：
        1. 用戶建立草稿文章
        2. 訂閱 postPublished
        3. 用戶發布文章
        4. 驗證訂閱者收到通知
        """
        from tests.factories import PostFactory
        from app.models.post import PostStatus

        # ==================== Arrange ====================
        # 📝 建立一篇草稿文章
        post = await PostFactory.create(
            test_session,
            author_id=test_user.id,
            title="待發布的文章",
            status=PostStatus.DRAFT,
        )
        await test_session.commit()

        # 📝 訂閱文章發布事件
        queue = PostEvent.subscribe()

        try:
            # ==================== Act ====================
            # 📝 透過 GraphQL mutation 發布文章
            mutation = """
                mutation PublishPost($id: ID!) {
                    publishPost(id: $id) {
                        id
                        title
                        status
                        publishedAt
                    }
                }
            """
            response = await authenticated_client.post(
                "/graphql",
                json={"query": mutation, "variables": {"id": str(post.id)}},
            )

            # ==================== Assert ====================
            # 📝 確認 mutation 成功
            assert response.status_code == 200
            data = response.json()
            assert "errors" not in data
            assert data["data"]["publishPost"]["status"] == "PUBLISHED"

            # 📝 確認訂閱者收到通知
            received_post = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert received_post.id == post.id
            assert received_post.title == "待發布的文章"
        finally:
            PostEvent.unsubscribe(queue)
