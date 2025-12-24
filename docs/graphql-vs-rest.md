# GraphQL vs RESTful API：深入淺出的比較

## 為什麼需要了解兩者的差異？

在現代 Web 開發中，API 是前後端溝通的橋樑。RESTful API 已經主導市場多年，而 GraphQL 作為後起之秀，提供了不同的思維方式。了解兩者的差異，能幫助我們在專案中做出更好的技術選擇。

## 核心概念對比

### 什麼是 REST？

REST（Representational State Transfer）是一種架構風格，把所有東西都視為「資源」，透過不同的 HTTP 方法來操作這些資源。

### 什麼是 GraphQL？

GraphQL 是一種查詢語言，讓客戶端能夠精確地要求所需的資料，不多不少。

### 基本差異一覽表

| 特性 | RESTful API | GraphQL |
|------|-------------|---------|
| **發布年份** | 2000 | 2015 (Facebook) |
| **端點數量** | 多個端點 | 單一端點 |
| **資料獲取** | 固定結構 | 彈性結構 |
| **HTTP 方法** | GET/POST/PUT/DELETE | 主要用 POST |
| **學習曲線** | 較平緩 | 較陡峭 |

## 實際範例比較：部落格系統

讓我們用一個實際的部落格系統來比較兩種 API 的差異。

### 場景：獲取文章及其作者資料

#### REST 方式

需要發送兩個請求：

```bash
# 1. 先獲取文章
GET /api/posts/123
回應：
{
  "id": 123,
  "title": "GraphQL 入門",
  "content": "...",
  "author_id": 456,
  "created_at": "2024-01-01"
}

# 2. 再獲取作者資料
GET /api/users/456
回應：
{
  "id": 456,
  "name": "王小明",
  "email": "wang@example.com",
  "bio": "...",
  "avatar": "..."
}
```

**問題：** 需要兩次網路請求（N+1 問題）

#### GraphQL 方式

只需要一個請求：

```graphql
query {
  post(id: 123) {
    id
    title
    content
    createdAt
    author {
      name
      email
    }
  }
}
```

回應：
```json
{
  "data": {
    "post": {
      "id": 123,
      "title": "GraphQL 入門",
      "content": "...",
      "createdAt": "2024-01-01",
      "author": {
        "name": "王小明",
        "email": "wang@example.com"
      }
    }
  }
}
```

**優點：** 一次請求就能獲得所有需要的資料，且只拿需要的欄位

### 場景：過度獲取（Over-fetching）問題

#### REST 的問題

```bash
GET /api/posts
# 回應包含所有欄位，即使你只需要標題
[
  {
    "id": 1,
    "title": "文章一",
    "content": "很長的內容...",  # 不需要但還是傳了
    "excerpt": "摘要...",         # 不需要但還是傳了
    "author_id": 123,             # 不需要但還是傳了
    "tags": [...],                # 不需要但還是傳了
    "created_at": "...",          # 不需要但還是傳了
    "updated_at": "..."           # 不需要但還是傳了
  },
  ...
]
```

#### GraphQL 的解決方案

```graphql
query {
  posts {
    id
    title  # 只要這兩個欄位
  }
}
```

### 場景：不足獲取（Under-fetching）問題

#### REST 的問題

想要顯示文章列表，包含作者名稱和評論數量：

```bash
# 1. 獲取文章列表
GET /api/posts

# 2. 對每篇文章獲取作者（假設有10篇文章）
GET /api/users/1
GET /api/users/2
...

# 3. 對每篇文章獲取評論數
GET /api/posts/1/comments/count
GET /api/posts/2/comments/count
...

# 總共需要 1 + 10 + 10 = 21 個請求！
```

#### GraphQL 的解決方案

```graphql
query {
  posts {
    id
    title
    author {
      name
    }
    commentCount  # 在後端計算好
  }
}
# 只需要 1 個請求！
```

## CRUD 操作對比

### 創建文章

#### REST 方式
```bash
POST /api/posts
Content-Type: application/json

{
  "title": "新文章",
  "content": "內容"
}
```

#### GraphQL 方式
```graphql
mutation {
  createPost(input: {
    title: "新文章"
    content: "內容"
  }) {
    id
    title
    createdAt
  }
}
```

### 更新文章

#### REST 方式
```bash
PUT /api/posts/123
Content-Type: application/json

{
  "title": "更新的標題"
}
```

#### GraphQL 方式
```graphql
mutation {
  updatePost(id: 123, input: {
    title: "更新的標題"
  }) {
    id
    title
    updatedAt
  }
}
```

### 刪除文章

#### REST 方式
```bash
DELETE /api/posts/123
```

#### GraphQL 方式
```graphql
mutation {
  deletePost(id: 123)
}
```

## API 設計哲學的差異

### REST 的資源導向思維

REST 把一切都當作資源，每個資源有自己的 URL：

```
/api/users        # 用戶資源
/api/posts        # 文章資源
/api/comments     # 評論資源
```

優點：
- 直觀易懂
- 符合 Web 的原生設計
- 容易快取（使用 HTTP 快取機制）

### GraphQL 的圖形化思維

GraphQL 把資料看作一個圖（Graph），節點之間有關聯：

```graphql
type User {
  posts: [Post!]!     # User 連接到 Post
  followers: [User!]! # User 連接到 User
}

type Post {
  author: User!       # Post 連接到 User
  comments: [Comment!]! # Post 連接到 Comment
}
```

優點：
- 更貼近實際的資料關係
- 靈活的查詢能力
- 強型別系統

## 優缺點深入分析

### RESTful API 的優勢

1. **簡單易學**
   - HTTP 方法語義清晰
   - 概念直觀

2. **成熟生態**
   - 工具豐富
   - 最佳實踐完善

3. **快取友好**
   - 可利用 HTTP 快取
   - CDN 支援良好

4. **無狀態設計**
   - 容易水平擴展
   - 服務器實現簡單

### RESTful API 的劣勢

1. **過度/不足獲取**
   - 固定的回應結構
   - 容易浪費頻寬

2. **多次往返**
   - N+1 查詢問題
   - 延遲累積

3. **版本管理**
   - API 演進困難
   - 需要維護多個版本

### GraphQL 的優勢

1. **精確獲取**
   - 客戶端決定資料結構
   - 減少頻寬浪費

2. **單一請求**
   - 一次獲取所有需要的資料
   - 減少網路延遲

3. **強型別系統**
   - 自動生成文件
   - 更好的開發體驗

4. **向後相容**
   - 新增欄位不影響舊客戶端
   - 透過 @deprecated 漸進式更新

### GraphQL 的劣勢

1. **複雜度較高**
   - 學習曲線陡峭
   - 需要專門的客戶端庫

2. **快取困難**
   - HTTP 快取機制不適用
   - 需要額外的快取策略

3. **安全考量**
   - 查詢複雜度攻擊
   - 需要實作深度限制

4. **檔案上傳**
   - 不如 REST 直觀
   - 需要額外處理

## 效能比較

### 網路效能

| 場景 | REST | GraphQL |
|------|------|---------|
| 簡單查詢 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 複雜關聯查詢 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 部分欄位更新 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 開發效率

| 面向 | REST | GraphQL |
|------|------|---------|
| 初期開發 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| API 演進 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 前後端協作 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 實際應用案例

### 適合使用 REST 的場景

1. **簡單的 CRUD 應用**
   - 資料結構固定
   - 關聯關係簡單

2. **公開 API**
   - 需要簡單易用
   - 第三方整合

3. **微服務間通訊**
   - 服務邊界清晰
   - 快取需求高

4. **檔案處理**
   - 上傳下載
   - 串流處理

### 適合使用 GraphQL 的場景

1. **複雜的前端應用**
   - 多種客戶端（Web、Mobile、Desktop）
   - 不同客戶端需要不同資料

2. **社交網路類應用**
   - 資料關聯複雜
   - 需要靈活查詢

3. **儀表板和報表**
   - 資料聚合需求
   - 客製化視圖

4. **快速迭代的產品**
   - 需求變化快
   - 需要向後相容

## 混合使用策略

在實際專案中，REST 和 GraphQL 可以共存：

```
/api/graphql       # GraphQL 端點（主要業務邏輯）
/api/upload        # REST 端點（檔案上傳）
/api/export        # REST 端點（資料匯出）
/api/webhooks      # REST 端點（第三方整合）
```

## 工具生態系統

### REST 工具

- **測試**：Postman, Insomnia
- **文件**：Swagger/OpenAPI
- **客戶端**：Axios, Fetch API

### GraphQL 工具

- **測試**：GraphQL Playground, Apollo Studio
- **文件**：自動生成（內建）
- **客戶端**：Apollo Client, Relay, urql

## 總結：如何選擇？

### 選擇 REST 如果你：

✅ 建構簡單的 API

✅ 團隊熟悉 REST

✅ 需要良好的快取

✅ 主要處理檔案

✅ 資源概念清晰

### 選擇 GraphQL 如果你：

✅ 有複雜的資料需求

✅ 多個客戶端類型

✅ 需要即時更新（[Subscriptions](./subscription-guide.md)）

✅ 想要更好的開發體驗

✅ 資料關聯複雜

## 結語

REST 和 GraphQL 都是優秀的 API 設計方案，沒有絕對的優劣，只有適不適合。

REST 以其簡單性和成熟度仍然是許多專案的首選，而 GraphQL 則為複雜的資料需求提供了優雅的解決方案。

---

## 延伸閱讀

- [GraphQL 官方文件](https://graphql.org/)
- [REST API 設計最佳實踐](https://restfulapi.net/)
- [從 REST 到 GraphQL 的實戰經驗](https://www.howtographql.com/)