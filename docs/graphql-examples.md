# GraphQL API 快速入門指南

本文檔提供 GraphQL API 的快速上手範例，可在 GraphQL Playground (<http://localhost:8000/graphql>) 中直接執行。

> 💡 **提示**: 更完整的使用範例請參考測試檔案，位於 `backend/tests/graphql/` 目錄，包含 22 個測試檔案涵蓋所有 API 功能。

## 快速開始

### 1. 設置認證

大部分操作需要認證。首先登入獲取 token：

```graphql
mutation Login {
  login(email: "user@example.com", password: "secure123") {
    token
    user {
      id
      username
    }
  }
}
```

在 GraphQL Playground 中設置 HTTP Headers：

```json
{
  "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
```

### 2. 基本查詢範例

```graphql
# 獲取當前用戶資訊
query Me {
  me {
    id
    username
    email
    bio
    followersCount
    followingCount
  }
}

# 獲取文章列表（只返回已發布文章）
query GetPosts {
  posts(limit: 10) {
    edges {
      node {
        id
        title
        author {
          username
        }
        likesCount
      }
    }
    pageInfo {
      totalCount
    }
  }
}
```

## 進階功能範例

### Fragment 重用（減少重複定義）

```graphql
fragment UserInfo on UserType {
  id
  username
  avatarUrl
}

fragment PostInfo on PostType {
  id
  title
  excerpt
  likesCount
}

query GetHomeFeed {
  posts(limit: 10) {
    edges {
      node {
        ...PostInfo
        author {
          ...UserInfo
        }
      }
    }
  }
}
```

### 使用變數的查詢（依標籤篩選文章）

```graphql
query GetPostsByTag($tagSlug: String!, $limit: Int = 10) {
  postsByTag(tagSlug: $tagSlug, limit: $limit) {
    edges {
      node {
        id
        title
        author {
          username
        }
      }
    }
  }
}

# Variables:
{
  "tagSlug": "graphql",
  "limit": 20
}
```

### Union Type 搜尋

```graphql
query Search($term: String!) {
  search(term: $term) {
    __typename
    ... on PostType {
      id
      title
      excerpt
    }
    ... on UserType {
      id
      username
      bio
    }
  }
}
```

Variables:
```json
{
  "term": "GraphQL"
}
```

### WebSocket 訂閱

```graphql
subscription OnCommentAdded {
  commentAdded(postId: "1") {
    id
    content
    author {
      username
    }
    createdAt
  }
}
```

```graphql
# 留言被編輯（推送完整留言，以 id 覆蓋內容）
subscription OnCommentUpdated {
  commentUpdated(postId: "1") {
    id
    content
    updatedAt
  }
}

# 留言被刪除（只推送 ID 與伺服器重新計算的留言數）
subscription OnCommentDeleted {
  commentDeleted(postId: "1") {
    commentId
    postId
    totalComments
  }
}
```

WebSocket 端點：`ws://localhost:8000/graphql`

## 錯誤處理

GraphQL 錯誤回應格式：

```json
{
  "errors": [{
    "message": "您沒有權限執行此操作",
    "extensions": {
      "code": "FORBIDDEN"
    }
  }]
}
```

## 效能優化提示

1. **使用 Fragment** - 減少重複的欄位定義
2. **限制查詢深度** - 避免過度嵌套
3. **使用分頁** - 處理大量資料時必要
4. **選擇性查詢** - 只請求需要的欄位
5. **DataLoader** - 後端自動處理批次載入

## 測試檔案導覽

詳細的使用範例請參考以下測試檔案：

- **認證**: `test_auth_mutations.py`, `test_auth_queries.py`
- **文章**: `test_post_queries.py`, `test_post_mutations.py`
- **評論**: `test_comment_queries.py`, `test_comment_mutations.py`
- **按讚**: `test_like_queries.py`, `test_like_mutations.py`
- **追蹤**: `test_follow_queries.py`, `test_follow_mutations.py`
- **搜尋**: `test_search_union.py`
- **訂閱**: `test_subscription_*.py`
- **Fragment**: `test_fragment_reuse.py`
- **DataLoader**: `test_dataloader_*.py`

## 常見問題

### Token 過期處理

目前 Token 過期後需要重新登入：

```graphql
mutation Login {
  login(email: "user@example.com", password: "secure123") {
    token
    user {
      id
      username
    }
  }
}
```

> 注意：Token 預設有效期為 7 天（可在後端環境變數 `ACCESS_TOKEN_EXPIRE_MINUTES` 中配置）

### 分頁參數說明

- `page`: 頁碼（從 1 開始）
- `limit`: 每頁數量

---

更多技術文檔請參考 `docs/` 目錄下的其他指南。
