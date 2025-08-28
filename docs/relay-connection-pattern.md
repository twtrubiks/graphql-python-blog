# Relay Connection Pattern 詳解

## 概述

Relay Connection Pattern 是 Facebook 在開發 Relay 框架時制定的 GraphQL 分頁規範，用於解決大規模資料分頁和關聯資訊儲存的問題。這個模式並非 GraphQL 本身的要求，而是一個被廣泛採用的最佳實踐。

## 核心概念

### 三層結構

```
Connection (連接)
├── edges[] (邊的集合)
│   ├── cursor (游標)
│   └── node (節點/實際資料)
└── pageInfo (分頁資訊)
    ├── hasNextPage
    ├── hasPreviousPage
    ├── startCursor
    └── endCursor
```

### 名詞解釋

- **Connection**: 代表一個分頁查詢的完整結果
- **Edge**: 包裝每個資料節點，可附加關聯資訊
- **Node**: 實際的資料物件
- **Cursor**: 不透明的字串，標記特定節點的位置
- **PageInfo**: 分頁的元資訊

## 為什麼需要 Edge？

### 1. 儲存關聯資訊

Edge 不只是簡單的包裝器，它可以儲存節點之間的關聯資訊：

```graphql
# 社交網路範例
type FriendEdge {
  cursor: String!
  node: User!              # 朋友本人
  friendsSince: DateTime!  # 成為朋友的時間（關聯資訊）
  mutualFriends: Int!      # 共同朋友數（關聯資訊）
}

# 電商購物車範例  
type CartItemEdge {
  cursor: String!
  node: Product!      # 商品
  quantity: Int!      # 數量（關聯資訊）
  addedAt: DateTime!  # 加入時間（關聯資訊）
  price: Float!       # 加入時的價格（關聯資訊）
}
```

### 2. 穩定的分頁

使用 cursor 而非 offset，即使資料變動也能準確定位：

```graphql
# 傳統 offset 分頁（資料變動時可能重複或遺漏）
query {
  posts(limit: 10, offset: 20) {
    id
    title
  }
}

# Relay cursor 分頁（資料變動不影響定位）
query {
  posts(first: 10, after: "YXJyYXk6MjA=") {
    edges {
      cursor
      node {
        id
        title
      }
    }
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}
```

## 實際應用範例

### GraphQL Schema 定義

```graphql
type Query {
  posts(
    first: Int
    after: String
    last: Int
    before: String
  ): PostConnection!
}

type PostConnection {
  edges: [PostEdge!]!
  pageInfo: PageInfo!
}

type PostEdge {
  cursor: String!
  node: Post!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

### 查詢範例

```graphql
# 取得前 5 篇文章
query FirstPage {
  posts(first: 5) {
    edges {
      cursor
      node {
        id
        title
        content
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}

# 取得下一頁（使用上一頁的 endCursor）
query NextPage {
  posts(first: 5, after: "YXJyYXk6NA==") {
    edges {
      cursor
      node {
        id
        title
        content
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

## 專案實作

### 目前的簡化版本

在我們的專案中，目前實作了簡化版的 Edge：

```python
# backend/app/graphql/types/post.py
@strawberry.type
class PostEdge:
    """Edge for post in connection"""
    node: PostType

@strawberry.type
class PostConnection:
    """Paginated post connection"""
    edges: List[PostEdge]
    page_info: PageInfo
```

### 使用範例

```python
# backend/app/graphql/queries/post.py
# 建立 edges
edges = [
    PostEdge(
        node=PostType.from_orm(post)
    )
    for post in posts
]

# 建立 connection
return PostConnection(
    edges=edges,
    page_info=PageInfo(
        has_next_page=has_next,
        has_previous_page=(page > 1),
        total_count=total,
        current_page=page,
        total_pages=total_pages
    )
)
```

## 優缺點分析

### 優點

1. **穩定性**: Cursor-based 分頁不受資料變動影響
2. **擴展性**: 可在 Edge 添加額外欄位而不影響 Node
3. **標準化**: Relay 客戶端可直接使用
4. **關聯資訊**: 可儲存節點間的關係資料

### 缺點

1. **複雜度**: 比簡單陣列分頁複雜
2. **無法跳頁**: 不能直接跳到第 N 頁
3. **學習曲線**: 需要理解 Connection/Edge/Node 概念

## 何時使用？

### 適合使用 Relay Pattern

- 資料即時變動頻繁（社交媒體動態）
- 需要儲存關聯資訊（朋友關係、購物車項目）
- 使用 Relay 或 Apollo Client
- 需要穩定的分頁體驗

### 可用簡單分頁

- 靜態資料（文章列表、產品目錄）
- 不需要關聯資訊
- 簡單的 CRUD 應用
- 需要跳頁功能

## 歷史背景

1. **2012-2015**: GraphQL 初期並無分頁規範
2. **2015**: Facebook 推出 Relay 框架，制定 Connection 規範
3. **原因**: Facebook 動態消息需要穩定分頁和關聯資訊
4. **現況**: 成為 GraphQL 生態系的事實標準

## 圖論基礎

Connection/Edge/Node 命名來自圖論（Graph Theory）：

```
User A ──[Friend Edge]──> User B
  ↑           ↑              ↑
 Node    關聯(Edge)        Node
```

- **Node（節點）**: 圖中的實體
- **Edge（邊）**: 節點之間的關聯
- **Connection（連接）**: 一組相關的邊

## 參考資源

### 外部資源
- [Relay Cursor Connections Specification](https://relay.dev/graphql/connections.htm)
- [GraphQL Cursor Connections Specification](https://graphql.org/learn/pagination/#complete-connection-model)
- [Understanding Relay Connections](https://www.apollographql.com/docs/react/pagination/cursor-based/)

### 專案相關文檔
- [GraphQL 介紹](./graphql-intro.md) - 了解 GraphQL 基礎概念
- [GraphQL vs REST](./graphql-vs-rest.md) - 比較 GraphQL 與 REST API 的差異
- [專案架構](./architecture.md) - 瞭解專案整體架構設計
- [測試範例](./tests-examples.md) - 查看分頁功能的測試實作
- [開發任務](./tasks.md) - 追蹤 Relay Pattern 相關開發進度