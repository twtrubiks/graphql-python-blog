# Relay Connection Pattern 詳解

## 快速理解

想像你在滑 Instagram：
- 每次載入 10 則貼文（分頁）
- App 記住你看到哪裡（游標）
- 每則貼文還有按讚數、留言數（額外資訊）
- 即使有人刪文，你繼續滑也不會看到重複內容（穩定性）

**一句話說明**：Relay Connection Pattern 就是一個「更聰明的分頁方式」，不只能翻頁，還能記住每個資料項目的額外資訊。

## 概述

Relay Connection Pattern 是 Facebook 在開發 Relay 框架時制定的 GraphQL 分頁規範。

為什麼要發明這個？因為 Facebook 的動態牆需要解決兩個問題：

1. 朋友一直發文、刪文，怎麼確保用戶不會看到重複內容？
2. 不只要顯示貼文，還要顯示「幾分鐘前發布」、「共同朋友按讚」等關聯資訊

## 核心概念

### 三層結構（用圖書館借書系統來理解）

```
查詢結果 (Connection) = 你的借書記錄查詢結果
├── 資料列表 (edges[]) = 每一筆借書記錄
│   ├── 位置標記 (cursor) = 記錄編號，像書籤一樣標記位置
│   └── 實際資料 (node) = 書本身的資訊
└── 翻頁資訊 (pageInfo) = 告訴你還有沒有更多記錄
    ├── hasNextPage = 還有下一頁嗎？
    ├── hasPreviousPage = 有上一頁嗎？
    ├── startCursor = 這一頁第一筆的位置
    └── endCursor = 這一頁最後一筆的位置
```

### 白話文解釋每個名詞

- **Connection（連接）**: 整包查詢結果，包含資料和翻頁資訊
- **Edge（邊）**: 每筆資料的包裝盒，可以放資料本身 + 額外資訊
- **Node（節點）**: 真正的資料內容（例如：文章、用戶、商品）
- **Cursor（游標）**: 加密的位置標記，像書籤一樣記住你看到哪裡
- **PageInfo（分頁資訊）**: 告訴你怎麼翻頁的資訊

## 為什麼需要 Edge？（為什麼要包一層？）

### 先看看實際例子 - 購物車

想像你的購物車，如果只存商品資料會怎樣？
```
❌ 只有商品資料：iPhone、AirPods、保護殼
```

但購物車需要更多資訊：
```
✅ 用 Edge 包裝後：
- iPhone × 2個，加入時間：今天10:30，當時價格：$30,000
- AirPods × 1個，加入時間：昨天14:20，當時價格：$5,000
- 保護殼 × 3個，加入時間：今天11:00，當時價格：$500
```

### 1. Edge 讓你可以儲存「關係資訊」

```graphql
# 朋友列表 - 不只要知道誰是朋友，還要知道什麼時候加的
type FriendEdge {
  cursor: String!
  node: User!              # 朋友本人的資料
  friendsSince: DateTime!  # 什麼時候成為朋友（這是關係資訊！）
  mutualFriends: Int!      # 有幾個共同朋友（這也是關係資訊！）
}

# 購物車 - 不只要商品，還要知道數量和價格
type CartItemEdge {
  cursor: String!
  node: Product!      # 商品本身
  quantity: Int!      # 買幾個（關係資訊）
  addedAt: DateTime!  # 何時加入購物車（關係資訊）
  price: Float!       # 加入時的價格，可能和現在不同（關係資訊）
}
```

### 2. 游標（Cursor）讓分頁更穩定

**傳統分頁的問題**：
```graphql
# 用頁碼分頁 - 如果有人刪文，第2頁的內容會變！
query {
  posts(limit: 10, offset: 20) {  # 跳過20筆，取10筆
    id
    title
  }
}
# 問題：如果第1頁有人刪了一篇文，原本第21篇會變成第20篇
# 結果：用戶可能看到重複的文章！
```

**Relay 的解決方式**：
```graphql
# 用游標分頁 - 即使有人刪文，也不會看到重複內容
query {
  posts(first: 10, after: "YXJyYXk6MjA=") {  # 這個奇怪字串是游標（位置標記）
    edges {
      cursor      # 每篇文章都有自己的位置標記
      node {
        id
        title
      }
    }
    pageInfo {
      endCursor     # 記住最後一篇的位置，下次從這裡繼續
      hasNextPage   # 還有下一頁嗎？
    }
  }
}
# 好處：游標直接指向特定文章，不受刪除影響
```

## 實際應用範例

### 這些程式碼在定義什麼？

```graphql
# 定義查詢介面
type Query {
  posts(
    first: Int        # 要幾筆資料
    after: String     # 從哪個位置開始（游標）
    last: Int         # 要最後幾筆
    before: String    # 在哪個位置之前
  ): PostConnection!  # 回傳文章連接物件
}

# 定義連接物件的結構
type PostConnection {
  edges: [PostEdge!]!     # 文章列表（每篇都包裝成 Edge）
  pageInfo: PageInfo!     # 翻頁資訊
}

# 定義每篇文章的包裝
type PostEdge {
  cursor: String!   # 這篇文章的位置標記
  node: Post!       # 文章本身
}

# 定義翻頁資訊
type PageInfo {
  hasNextPage: Boolean!      # 還有下一頁嗎？
  hasPreviousPage: Boolean!  # 有上一頁嗎？
  startCursor: String        # 這一頁第一筆的位置
  endCursor: String          # 這一頁最後一筆的位置
}
```

### 實際查詢怎麼寫？

```graphql
# 情境：第一次載入，取 5 篇文章
query FirstPage {
  posts(first: 5) {         # 取前 5 篇
    edges {
      cursor                # 每篇的位置標記
      node {
        id
        title
        content
      }
    }
    pageInfo {
      hasNextPage           # 看看還有沒有更多文章
      endCursor            # 記住最後一篇的位置（等下要用）
    }
  }
}

# 情境：用戶往下滑，載入更多
query NextPage {
  posts(
    first: 5,
    after: "YXJyYXk6NA=="   # 用上一次的 endCursor，從那裡繼續
  ) {
    edges {
      cursor
      node {
        id
        title
        content
      }
    }
    pageInfo {
      hasNextPage          # 還有更多嗎？
      endCursor           # 記住新的最後位置
    }
  }
}
```

## 在我們專案中的實作

### 混合模式：Relay 結構 + 頁碼分頁

本專案採用**混合模式**，結合了 Relay Connection Pattern 的結構優點與傳統頁碼分頁的便利性：

- ✅ 使用 Relay 的三層結構（Connection → Edge → Node）
- ✅ 支援跳頁功能（傳統分頁優勢）
- ❌ 不使用 cursor（簡化實作）

這種方式適合部落格等資料變動頻率較低的應用。

```python
# backend/app/graphql/types/post.py

@strawberry.type
class PageInfo:
    """分頁資訊 - 採用頁碼模式而非游標模式"""
    has_next_page: bool       # 還有下一頁嗎？
    has_previous_page: bool   # 有上一頁嗎？
    total_count: int          # 總共幾篇文章
    current_page: int         # 現在第幾頁
    total_pages: int          # 總共幾頁

@strawberry.type
class PostEdge:
    """文章的包裝盒"""
    node: PostType    # 文章本身

@strawberry.type
class PostConnection:
    """查詢結果的完整包裝"""
    edges: List[PostEdge]    # 文章列表（每篇都用 Edge 包裝）
    page_info: PageInfo      # 翻頁資訊
```

### 實際使用時怎麼包裝資料？

```python
# backend/app/graphql/queries/post.py
# 這段程式碼示範如何把資料庫的文章包裝成 Relay 格式

# 計算分頁資訊
total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
has_next_page = page < total_pages
has_previous_page = page > 1

# 步驟 1：把每篇文章包裝成 Edge
edges = [
    PostEdge(node=PostType.from_orm(post))
    for post in posts  # posts 是從資料庫查出來的文章列表
]

# 步驟 2：建立分頁資訊
page_info = PageInfo(
    has_next_page=has_next_page,
    has_previous_page=has_previous_page,
    total_count=total_count,
    current_page=page,
    total_pages=total_pages
)

# 步驟 3：回傳完整的連接物件
return PostConnection(
    edges=edges,
    page_info=page_info
)
```

## 優缺點對比

| 特點 | Relay (Cursor) | 混合模式（本專案） | 傳統分頁 |
|------|---------------|------------------|----------|
| 穩定性 | ✅ 資料變動不影響 | ⚠️ 同傳統分頁 | ❌ 可能看到重複內容 |
| 額外資訊 | ✅ 可儲存關係資料 | ✅ 可儲存關係資料 | ❌ 只有資料本身 |
| 跳頁 | ❌ 不能跳到第N頁 | ✅ 可以直接跳頁 | ✅ 可以直接跳頁 |
| 複雜度 | ❌ 需要理解三層結構 | ⚠️ 中等 | ✅ 簡單直覺 |
| 標準化 | ✅ 業界標準 | ⚠️ 非標準 | ❌ 各家不同 |
| 適用場景 | 社交動態牆 | 部落格、CMS | 簡單列表 |

**一句話總結**：

- **社交應用**（資料頻繁變動）→ 用完整 Relay (Cursor)
- **部落格/CMS**（需要結構化但變動少）→ 用混合模式（本專案採用）
- **簡單列表**（快速開發）→ 用傳統分頁

## 我的專案需要用這個嗎？

### ✅ 建議使用 Relay Pattern 的情境

1. **社交應用**
   - 動態牆、留言、按讚
   - 原因：資料隨時在變，需要穩定分頁

2. **購物車/訂單**
   - 商品數量、加入時間、當時價格
   - 原因：需要儲存關係資訊

3. **即時通訊**
   - 訊息已讀、發送時間
   - 原因：需要額外資訊 + 穩定性

4. **使用 Relay/Apollo Client**
   - 這些框架原生支援此模式
   - 原因：開箱即用，不用自己實作

### ❌ 可以用簡單分頁的情境

1. **靜態內容**
   - 部落格文章、產品目錄
   - 原因：資料不常變，不需要額外資訊

2. **後台管理**
   - 用戶列表、訂單管理
   - 原因：需要跳頁功能

3. **小型專案**
   - 個人網站、簡單 CRUD
   - 原因：不值得增加複雜度

## 常見問題 Q&A

**Q: 游標（Cursor）裡面是什麼？**
A: 通常是 base64 編碼的位置資訊，例如 `YXJyYXk6MjA=` 解碼後可能是 `array:20`，代表第20個項目。

**Q: 一定要用這麼複雜的結構嗎？**
A: 不一定！如果你的應用很簡單，用傳統分頁就好。這是為了解決大型應用的問題而設計的。

**Q: Edge 可以加什麼資訊？**
A: 任何「關係」相關的資訊都可以，例如：加入時間、順序、權重、狀態等。

**Q: 為什麼不能跳頁？**
A: 因為游標是連續的，你必須從頭開始一頁一頁往下走，無法直接跳到第10頁。

## 背景知識

### 為什麼叫 Connection/Edge/Node？

這些名詞來自「圖論」（Graph Theory）- 研究點和線關係的數學分支：

```
朋友關係圖：
小明 ──[成為朋友於2020]──> 小華
  ↑           ↑              ↑
 節點      關係(邊)         節點
```

- **Node（節點）** = 圖中的點 = 實體（人、文章、商品）
- **Edge（邊）** = 連接點的線 = 關係
- **Connection（連接）** = 一組相關的邊 = 查詢結果

### 歷史小故事

2015年，Facebook 工程師在開發動態牆時遇到問題：用戶滑動時如果有人刪文或發文，傳統分頁會讓用戶看到重複內容。於是他們發明了這個模式，並放在 Relay 框架中。現在這已經成為 GraphQL 的標準做法。

## 參考資源

### 外部資源
- [Relay Cursor Connections Specification](https://relay.dev/graphql/connections.htm)
- [GraphQL Cursor Connections Specification](https://graphql.org/learn/pagination/#complete-connection-model)
- [Understanding Relay Connections](https://www.apollographql.com/docs/react/pagination/cursor-based/)

### 專案相關文檔
- [GraphQL 介紹](./graphql-intro.md) - 了解 GraphQL 基礎概念
- [GraphQL vs REST](./graphql-vs-rest.md) - 比較 GraphQL 與 REST API 的差異
- [專案架構](./architecture.md) - 瞭解專案整體架構設計
- [開發任務](./tasks.md) - 追蹤 Relay Pattern 相關開發進度