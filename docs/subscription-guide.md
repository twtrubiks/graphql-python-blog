# GraphQL Subscription 實作指南

本專案使用 `commentAdded` subscription 實現即時評論通知。

---

## 架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                         資料流程                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [用戶 A 發送評論]                                               │
│        │                                                        │
│        ▼                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Mutation   │───▶│ CommentEvent │───▶│   Queue(s)   │      │
│  │ add_comment  │    │   .publish() │    │  (訂閱者們)   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                 │                │
│                                                 ▼                │
│                                          WebSocket 推送          │
│                                                 │                │
│                                                 ▼                │
│                                    ┌──────────────────┐         │
│                                    │  用戶 B 的前端    │         │
│                                    │  即時收到新評論   │         │
│                                    └──────────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 後端實作

### 檔案結構

| 檔案 | 職責 |
|-----|------|
| `backend/app/graphql/subscriptions/comment.py` | 事件管理器 + Subscription Resolver |
| `backend/app/graphql/mutations/comment.py` | 在 mutation 中發布事件 |

### 1. 事件管理器 (CommentEvent)

```python
# backend/app/graphql/subscriptions/comment.py

class CommentEvent:
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
        """發布新評論事件給所有訂閱者"""
        if post_id in cls._subscribers:
            for queue in cls._subscribers[post_id]:
                await queue.put(comment)
```

### 2. Subscription Resolver

```python
# backend/app/graphql/subscriptions/comment.py

@strawberry.type
class CommentSubscription:
    @strawberry.subscription
    async def comment_added(self, post_id: strawberry.ID) -> AsyncGenerator[Comment, None]:
        post_id_str = str(post_id)
        queue = CommentEvent.subscribe(post_id_str)
        try:
            while True:
                comment = await queue.get()
                yield comment
        finally:
            CommentEvent.unsubscribe(post_id_str, queue)
```

### 3. 在 Mutation 中觸發

```python
# backend/app/graphql/mutations/comment.py:45

# 發送即時通知給訂閱者
await CommentEvent.publish(str(post_id), comment_type)
```

---

## 前端實作

### 檔案結構

| 檔案 | 職責 |
|-----|------|
| `frontend/src/lib/graphql/subscriptions/CommentAdded.gql` | GraphQL subscription 定義 |
| `frontend/src/routes/posts/[slug]/+page.svelte` | 訂閱生命週期管理 |

### 1. GraphQL 定義

```graphql
# frontend/src/lib/graphql/subscriptions/CommentAdded.gql

subscription CommentAdded($postId: ID!) {
  commentAdded(postId: $postId) {
    id
    content
    createdAt
    updatedAt
    isDeleted
    author { id, username, avatarUrl }
    post { id, totalComments }
  }
}
```

### 2. Houdini Store 訂閱

```typescript
// frontend/src/routes/posts/[slug]/+page.svelte

import { CommentAddedStore } from '$houdini';

const commentAddedStore = new CommentAddedStore();

// 狀態管理
let subscriptionStatus = $state<'idle' | 'connecting' | 'connected' | 'error'>('idle');
let currentPostId = $state<string | null>(null);

// 開始監聽（當 postId 變化時）
$effect(() => {
  if (!post?.id || currentPostId === String(post.id)) return;
  currentPostId = String(post.id);
  subscriptionStatus = 'connecting';

  commentAddedStore.listen({ postId: currentPostId })
    .then(() => { subscriptionStatus = 'connected'; })
    .catch(() => { subscriptionStatus = 'error'; });
});

// 監聽資料變化
onMount(() => {
  storeUnsubscribe = commentAddedStore.subscribe((value) => {
    if (value.data?.commentAdded) {
      handleNewComment({ commentAdded: value.data.commentAdded });
    }
  });
});

// 清理
onDestroy(async () => {
  storeUnsubscribe?.();
  await commentAddedStore.unlisten?.();
});
```

---

## 訂閱生命週期

```
┌─────────────────────────────────────────────────────────┐
│                    前端訂閱生命週期                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  組件載入                                                │
│      │                                                  │
│      ▼                                                  │
│  ┌─────────────────┐                                    │
│  │ $effect 觸發     │  ← postId 變化時重新建立           │
│  │ store.listen()  │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ onMount         │                                    │
│  │ store.subscribe │  ← 監聽資料變化                     │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ 收到新評論       │  → handleNewComment()              │
│  │ 更新 UI         │  → 顯示通知                         │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ onDestroy       │                                    │
│  │ store.unlisten  │  ← 清理 WebSocket 連線              │
│  └─────────────────┘                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 連線狀態指示器

前端實作了視覺化的連線狀態（參考 `+page.svelte:549-576`）：

| 狀態 | 顯示 |
|-----|------|
| `connecting` | 旋轉圖示 + "連線中..." |
| `connected` | 綠色脈衝圓點 + "已連線" |
| `error` | 重連嘗試 or 錯誤訊息 |

---

## 相關檔案索引

```
backend/
├── app/graphql/
│   ├── subscriptions/
│   │   └── comment.py          # CommentEvent + CommentSubscription
│   ├── mutations/
│   │   └── comment.py:45       # 發布事件
│   └── schema.py               # 整合 Subscription 類

frontend/
├── src/lib/graphql/subscriptions/
│   └── CommentAdded.gql        # GraphQL 定義
└── src/routes/posts/[slug]/
    └── +page.svelte:38-152     # 訂閱生命週期管理
```

---

## 其他 Subscription 實作

本專案還實作了以下 subscription，皆遵循相同的事件管理器模式：

### postPublished - 新文章發布通知

```graphql
subscription PostPublished {
  postPublished {
    id
    title
    slug
    author { username }
  }
}
```

**檔案位置**：`backend/app/graphql/subscriptions/post.py`

### followedUserPosted - 追蹤用戶發文通知

```graphql
subscription FollowedUserPosted {
  followedUserPosted {
    id
    title
    author { username }
  }
}
```

**檔案位置**：`backend/app/graphql/subscriptions/followed_user_post.py`

### postDeleted - 文章刪除通知

```graphql
subscription PostDeleted {
  postDeleted
}
```

**檔案位置**：`backend/app/graphql/subscriptions/post_deleted.py`

### userStatus - 用戶在線狀態訂閱 ⭐

即時追蹤用戶的在線/離線狀態，支援多分頁連線計數。

```graphql
subscription UserStatus($userId: ID, $username: String) {
  userStatus(userId: $userId, username: $username) {
    userId
    username
    isOnline
    lastSeen
  }
}
```

**檔案位置**：`backend/app/graphql/subscriptions/user_status.py`

**特點**：
- 支援 `userId` 或 `username` 參數訂閱特定用戶狀態
- 連線計數器處理多分頁情境（同一用戶開多個分頁不會誤判離線）
- 前端全局訂閱（在 Layout 層級）
- UserCard 組件顯示綠色在線狀態指示器

**前端整合**：

| 檔案 | 職責 |
|-----|------|
| `frontend/src/lib/graphql/subscriptions/UserStatus.gql` | GraphQL subscription 定義 |
| `frontend/src/lib/stores/userStatus.svelte.ts` | 用戶狀態 store |
| `frontend/src/routes/+layout.svelte` | 全局訂閱管理 |
| `frontend/src/lib/components/UserCard.svelte` | 在線狀態指示器 UI |
| `frontend/src/lib/utils/subscriptionManager.svelte.ts` | 通用訂閱管理器 |

**初始狀態查詢**：

訂閱只會接收「變化」事件，新訂閱者需透過 query 取得當前狀態：

```graphql
query GetOnlineUsers {
  onlineUsers {
    userId
    username
  }
}
```

---

## 訂閱管理器 (subscriptionManager)

解決 `$effect`/`onMount` 競爭條件導致的重複初始化問題。

**使用方式**：

```typescript
import { createSubscriptionManager } from '$lib/utils/subscriptionManager.svelte';

const manager = createSubscriptionManager({
  name: 'UserStatus',
  createStore: () => new UserStatusStore(),
  getListenParams: () => auth.user ? { userId: auth.user.id } : null,
  onData: (data) => handleStatusChange(data),
  requiresAuth: true
});

// 在 $effect 中初始化（自動防重複）
$effect(() => {
  if (auth.user) manager.init();
});

// 清理
onDestroy(() => manager.cleanup());
```

**核心功能**：
- 防重複初始化（`isInitialized` 狀態鎖）
- 統一生命週期管理（init → start → cleanup）
- 支援認證檢查（`requiresAuth`）

---

## ⚠️ 限制與擴展方案

### 目前實作的限制

本專案使用 **記憶體內的 asyncio.Queue** 管理訂閱者：

```python
class PostEvent:
    _subscribers: list[asyncio.Queue] = []  # ← 記憶體中的類別變數
```

**限制說明：**

| 限制 | 說明 |
|------|------|
| 記憶體儲存 | `_subscribers` 儲存在 Server 記憶體中 |
| 重啟清空 | 重啟 Server 後，所有訂閱狀態會清空 |
| 單機限制 | **僅適用於單機部署** |

> **注意**：重啟 Server 時 WebSocket 連線本就會斷開，客戶端會自動重連並重新訂閱，因此單機情境下這不是問題。

### 多機部署問題

當使用多台 Server 負載均衡時，會發生訂閱隔離問題：

```
┌──────────────────────────────────────────────────────────┐
│                    負載均衡器                              │
└─────────────────┬────────────────────┬───────────────────┘
                  │                    │
                  ▼                    ▼
         ┌──────────────┐      ┌──────────────┐
         │   Server A   │      │   Server B   │
         │ _sub = [A]   │      │ _sub = [B]   │
         │ 用戶A 連這台  │      │ 用戶B 連這台  │
         └──────────────┘      └──────────────┘

問題：用戶A 發文時，PostEvent.publish() 只會通知 Server A 的訂閱者
     → 用戶B 收不到通知！
```

### 擴展方案

根據規模選擇適合的方案：

| 方案 | 適用場景 | 複雜度 | 說明 |
|------|---------|--------|------|
| **目前方式** | 單機部署、開發環境 | ⭐ 簡單 | 無需額外依賴 |
| **Redis Pub/Sub** | 多台 Server | ⭐⭐ 中等 | 輕量級，適合大多數場景 |
| **Kafka/RabbitMQ** | 大規模、高可用 | ⭐⭐⭐ 複雜 | 訊息持久化、重播能力 |

### Redis Pub/Sub 實作範例

若需要支援多機部署，可改用 Redis 作為訊息中介：

```python
# 概念範例（需安裝 redis 套件）
import aioredis

class PostEventRedis:
    """使用 Redis Pub/Sub 的事件管理器"""

    CHANNEL = "post_events"

    @classmethod
    async def publish_post(cls, post: PostType):
        """發布到 Redis Channel"""
        redis = await aioredis.from_url("redis://localhost")
        await redis.publish(cls.CHANNEL, post.json())
        await redis.close()

    @classmethod
    async def subscribe(cls) -> AsyncGenerator[PostType, None]:
        """訂閱 Redis Channel"""
        redis = await aioredis.from_url("redis://localhost")
        pubsub = redis.pubsub()
        await pubsub.subscribe(cls.CHANNEL)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    post_data = json.loads(message["data"])
                    yield PostType(**post_data)
        finally:
            await pubsub.unsubscribe(cls.CHANNEL)
            await redis.close()
```

**Redis 方案優點：**

```
┌──────────────────────────────────────────────────────────┐
│                    負載均衡器                              │
└─────────────────┬────────────────────┬───────────────────┘
                  │                    │
                  ▼                    ▼
         ┌──────────────┐      ┌──────────────┐
         │   Server A   │      │   Server B   │
         │   用戶A      │      │   用戶B      │
         └───────┬──────┘      └───────┬──────┘
                 │                     │
                 └──────────┬──────────┘
                            ▼
                    ┌──────────────┐
                    │    Redis     │
                    │   Pub/Sub    │
                    └──────────────┘

用戶A 發文 → Redis 廣播 → 所有 Server 收到 → 所有用戶收到 ✅
```

### 選擇建議

```
你的使用情境是？

├── 開發/測試環境
│   └── ✅ 使用目前方式（記憶體 Queue）
│
├── 單機生產環境
│   └── ✅ 使用目前方式（記憶體 Queue）
│
├── 多機部署（2-10 台）
│   └── ✅ 使用 Redis Pub/Sub
│
└── 大規模部署（10+ 台）/ 需要訊息持久化
    └── ✅ 使用 Kafka 或 RabbitMQ
```

---

## 延伸閱讀

- [Strawberry GraphQL Subscriptions](https://strawberry.rocks/docs/general/subscriptions)
- [Houdini Subscriptions](https://houdinigraphql.com/guides/subscriptions)
- [Redis Pub/Sub 官方文檔](https://redis.io/docs/manual/pubsub/)
- [aioredis Python 套件](https://aioredis.readthedocs.io/)
