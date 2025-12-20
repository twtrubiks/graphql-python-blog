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

---

## 延伸閱讀

- [Strawberry GraphQL Subscriptions](https://strawberry.rocks/docs/general/subscriptions)
- [Houdini Subscriptions](https://houdinigraphql.com/guides/subscriptions)
