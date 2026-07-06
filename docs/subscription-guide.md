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
    ...CommentInfo @mask_disable
    post {
      id
      totalComments
    }
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

// 重連機制：失敗後以 2s/4s/6s 遞增間隔重試，最多 3 次
const MAX_RECONNECT_ATTEMPTS = 3;
let reconnectAttempts = $state(0);
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleReconnect(postId: string) {
  if (reconnectTimer || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
  reconnectAttempts += 1;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (currentPostId === postId) startSubscription(postId);
  }, 2000 * reconnectAttempts);
}

async function startSubscription(postId: string) {
  // Houdini 對相同變數重複 listen 會直接略過，重連前先 unlisten 重置其內部狀態
  await commentAddedStore.unlisten();
  // await 期間文章已切換或元件已銷毀時放棄
  if (currentPostId !== postId) return;
  await commentAddedStore.listen({ postId });
  if (currentPostId !== postId) return;
  // 錯誤時 listen 也可能正常 resolve（錯誤事後才走 store 的 errors 路徑），
  // 不能在這裡重置 reconnectAttempts，否則失敗的重連會不斷歸零、永遠達不到重試上限
  if (!reconnectTimer) subscriptionStatus = 'connected';
}

// 開始監聽（當 postId 變化時）
$effect(() => {
  if (!post?.id || currentPostId === String(post.id)) return;
  currentPostId = String(post.id);
  reconnectAttempts = 0;
  subscriptionStatus = 'connecting';
  startSubscription(currentPostId);
});

// 監聽資料變化
onMount(() => {
  storeUnsubscribe = commentAddedStore.subscribe((value) => {
    if (value.data?.commentAdded) {
      // 連線其實活著：重置計數並取消已排定的重連
      subscriptionStatus = 'connected';
      reconnectAttempts = 0;
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
      handleNewComment({ commentAdded: value.data.commentAdded });
    }
    // 注意：Houdini 的錯誤欄位是 errors「陣列」（成功時為空陣列），沒有 value.error
    if (value.errors?.length) {
      subscriptionStatus = 'error';
      if (currentPostId) scheduleReconnect(currentPostId);
    }
  });
});

// 清理
onDestroy(async () => {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  currentPostId = null;  // 讓已排定的重連 timer 觸發時直接放棄
  storeUnsubscribe?.();
  await commentAddedStore.unlisten?.();
});
```

### 3. 與 addComment mutation 的分工

自己的留言**不依賴 subscription 回填**：`handleAddComment` 在 mutation 成功後，直接用回傳的 comment 呼叫 `handleNewComment` 做本地插入，因此即使 WebSocket 斷線（被防火牆/代理阻擋等），留言仍會立即顯示。subscription 定位為「別人留言」的即時管道；當訂閱把自己剛發的留言推回來時，`handleNewComment` 內的 id 去重會擋掉重複插入。

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

前端實作了視覺化的連線狀態（參考 `+page.svelte:718-745`）：

| 狀態 | 顯示 |
|-----|------|
| `connecting` | 旋轉圖示 + "即時更新連線中..." |
| `connected` | 綠色脈衝圓點 + "即時更新已連線" |
| `error`（重連中） | 橘色旋轉圖示 + "重新連線中... (嘗試 N/3)" |
| `error`（重連耗盡） | 紅色圖示 + "即時更新暫時無法使用" |

### 斷線重連

連線失敗時會自動重連，最多 3 次，間隔 2s → 4s → 6s 遞增；只有**真正收到新資料**時才重置計數。實作上有三個陷阱要注意：

1. **錯誤欄位是 `errors` 陣列**（成功的訊息也會帶空陣列），`value.error` 這個欄位不存在，判斷時必須用 `value.errors?.length`。
2. **對相同變數重複呼叫 `listen()` 會被 Houdini 內部略過**（`variablesChanged` + session 比對），因此重連前必須先 `await unlisten()` 重置其內部狀態，否則重連是 no-op。
3. **`listen()` resolve 不代表連線成功**（失敗時錯誤事後才走 store 的 `errors` 路徑），因此重試計數不能在 resolve 時歸零，否則失敗的重連會不斷重置計數、永遠達不到重試上限；此外 `await` 期間文章可能已切換或元件已銷毀，續行前要再檢查 `currentPostId`。

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
    └── +page.svelte:54-216     # 訂閱生命週期管理（含斷線重連）
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
    slug
    excerpt
    author { username }
  }
}
```

**檔案位置**：`backend/app/graphql/subscriptions/followed_user_post.py`

**特點**：
- 需要認證：訂閱者身分取自 WebSocket 連線的 JWT（`connectionParams`），不接受客戶端指定，未登入會收到 `Authentication required` 錯誤
- 只會推送追蹤的作者發布的文章

### postDeleted - 文章刪除通知

```graphql
subscription PostDeleted {
  postDeleted
}
```

**檔案位置**：`backend/app/graphql/subscriptions/post_deleted.py`

**特點**：
- 需要認證：訂閱者身分取自 WebSocket 連線的 JWT（`connectionParams`），不接受客戶端指定
- 返回被刪除的文章 ID
- 用於即時更新 /following 頁面

### userStatusChanged - 用戶在線狀態訂閱 ⭐

即時追蹤用戶的在線/離線狀態，支援多分頁連線計數。

```graphql
subscription UserStatusChanged {
  userStatusChanged {
    userId
    username
    status
    timestamp
  }
}
```

**檔案位置**：`backend/app/graphql/subscriptions/user_status.py`

**特點**：
- 需要認證：`userId` 取自 WebSocket 連線的 JWT，`username` 由資料庫查出，皆不接受客戶端指定（防止偽造他人上線狀態）
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
  // 回傳 null 表示不滿足啟動條件；身分由後端從 WebSocket 認證資訊判定
  getListenParams: () => auth.user ? {} : null,
  createStore: () => new UserStatusStore(),
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
| 單行程限制 | **僅適用於單行程部署**（`uvicorn --workers N` 的多 worker 也是多行程，事件不會跨 worker 廣播，同樣需要下方的擴展方案） |

> **注意**：重啟 Server 時 WebSocket 連線本就會斷開，客戶端會自動重連並重新訂閱，因此單機情境下這不是問題。

> **記憶體管理**：`UserStatusEvent` 的 `_user_status` / `_user_info` / `_user_connections` 字典會在用戶完全斷線（連線數歸零）時清除該用戶的記錄，避免長時間運行下無上限累積。

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
