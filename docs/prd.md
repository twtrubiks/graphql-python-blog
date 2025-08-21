# GraphQL 部落格平台 - 產品需求文件 (PRD)

## 專案概述

### 專案名稱
GraphQL Blog Platform Tutorial

### 專案目標
建立一個現代化的部落格平台，作為 GraphQL + Python 的完整教學範例，展示前後端整合的最佳實踐。

### 技術規格
- **Python**: 3.13 (最新版)
- **後端**: FastAPI + Strawberry + SQLAlchemy 2.0 + PostgreSQL 16
- **前端**: SvelteKit 2.x + Svelte 5 (Runes) + Houdini
- **進階**: pgvector (第二階段)

## 核心功能需求

### Phase 1: 基礎功能 (MVP)

#### 1. 用戶系統
- 註冊 (email + password)
- 登入/登出 (JWT)
- 個人資料頁面
- 作者簡介

#### 2. 文章管理
- 發表文章 (Markdown 格式)
- 編輯/刪除自己的文章
- 文章列表 (分頁)
- 文章詳情頁
- 草稿功能

#### 3. 互動功能
- 評論系統
- 按讚功能
- 文章標籤
- 分類瀏覽

#### 4. 搜尋功能
- 關鍵字搜尋
- 標籤篩選
- 作者篩選

### Phase 2: 進階功能

#### 5. 社交功能
- 追蹤作者
- 熱門文章排行

#### 6. 內容增強
- 圖片上傳 (文章封面 - 本地儲存)
- 程式碼高亮
- 閱讀時間估算
- 目錄自動生成

#### 7. AI 功能 (pgvector - 選用)
- 語義搜尋
- 相似文章推薦
- 自動標籤建議
- 重複內容檢測

## 技術架構

### 核心技術棧
- **後端**: FastAPI + Strawberry (GraphQL) + SQLAlchemy 2.0
- **資料庫**: PostgreSQL 16
- **前端**: SvelteKit + Houdini (GraphQL Client)
- **進階**: pgvector (選用 - 語義搜尋)

### GraphQL Schema

#### 核心設計原則
1. **單一入口點**：所有操作通過 `/graphql`
2. **強型別定義**：每個欄位都有明確型別
3. **關係導航**：可從任意節點導航到相關資料
4. **計算欄位**：動態計算而非存儲的資料

```graphql
type Query {
  # 文章查詢 - 展示分頁、篩選能力
  posts(
    page: Int = 1
    limit: Int = 10
    tag: String
    authorId: ID
  ): PostConnection!  # Connection Pattern 用於分頁

  post(id: ID, slug: String): Post

  # 用戶查詢 - 展示認證整合
  me: User  # 需要認證，從 context 獲取當前用戶
  user(id: ID, username: String): User
  users(page: Int = 1, limit: Int = 10): UserConnection!

  # 搜尋 - 展示聯合型別
  search(
    query: String!
    type: SearchType = ALL
    semantic: Boolean = false  # 選用：向量搜尋
  ): SearchResult!

  # 標籤
  tags(popular: Boolean = false): [Tag!]!
}

type Mutation {
  # 認證
  register(input: RegisterInput!): AuthPayload!
  login(email: String!, password: String!): AuthPayload!
  logout: Boolean!
  refreshToken(token: String!): AuthPayload!

  # 文章操作
  createPost(input: PostInput!): Post!
  updatePost(id: ID!, input: PostInput!): Post!
  deletePost(id: ID!): Boolean!
  publishPost(id: ID!): Post!

  # 互動
  likePost(postId: ID!): Post!
  unlikePost(postId: ID!): Post!
  createComment(postId: ID!, content: String!): Comment!
  deleteComment(id: ID!): Boolean!

  # 社交
  followUser(userId: ID!): User!
  unfollowUser(userId: ID!): User!

  # 個人資料
  updateProfile(input: ProfileInput!): User!
  uploadAvatar(file: Upload!): User!
}

type Subscription {
  # 即時更新
  commentAdded(postId: ID!): Comment!
  postPublished(authorId: ID): Post!
}

type Post {
  id: ID!
  title: String!
  slug: String!
  content: String!
  excerpt: String!
  author: User!  # Resolver: 解析作者資料
  status: PostStatus!
  tags: [Tag!]!  # Resolver: 批次載入標籤
  likes: Int!  # 計算欄位：統計按讚數
  isLiked: Boolean!  # 計算欄位：當前用戶是否按讚
  comments: [Comment!]!  # Resolver: 載入評論
  createdAt: DateTime!
  updatedAt: DateTime!
  readTime: Int!  # 計算欄位：根據字數計算
  similarPosts(limit: Int = 5): [Post!]!  # 選用：向量相似度
}

type User {
  id: ID!
  email: String!
  username: String!
  bio: String
  avatarUrl: String
  posts(page: Int = 1, limit: Int = 10): PostConnection!  # 分頁查詢
  followers: [User!]!  # Resolver: 載入追蹤者
  following: [User!]!  # Resolver: 載入追蹤中
  isFollowing: Boolean!  # 計算欄位：當前用戶是否追蹤
  createdAt: DateTime!
}

# Connection Pattern 用於分頁
type PostConnection {
  edges: [PostEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type PostEdge {
  node: Post!
  cursor: String!
}

enum PostStatus {
  DRAFT
  PUBLISHED
}

enum SearchType {
  ALL
  POSTS
  USERS
  TAGS
}
```

### GraphQL 客戶端整合

前端使用 **Houdini** 作為 GraphQL 客戶端，提供：
- 自動型別生成
- 編譯時查詢優化
- 內建快取管理
- SvelteKit 深度整合

## 非功能性需求

### 效能要求
- GraphQL 查詢回應時間 < 200ms
- 首頁載入時間 < 2s
- Lighthouse 分數 > 90
- 支援 100+ 同時在線用戶
- 資料庫查詢優化（使用索引）

### 安全要求
- JWT token 過期時間：Access Token 15分鐘，Refresh Token 7天
- SQL Injection 防護（使用 ORM）
- XSS 防護（內容消毒）
- CORS 設定
- 密碼加密（bcrypt）
- 輸入驗證

### 開發體驗
- 完整的 TypeScript 型別提示
- Hot Module Replacement (HMR)
- GraphQL Playground/GraphiQL
- 自動化測試（單元測試 + 整合測試）
- Pre-commit hooks（格式化、lint）
- 詳細的錯誤訊息

### 可擴展性
- 微服務架構預留
- 資料庫水平擴展支援
- 快取層設計（選用）
- CDN 整合預留

## 開發階段規劃

### 階段一：GraphQL 基礎建置
- GraphQL Schema 設計與定義
- Query 與 Mutation 實作
- Resolver 架構建立
- DataLoader 整合（解決 N+1 問題）
- 基本 CRUD 操作

### 階段二：GraphQL 進階功能
- Subscription 實作（即時更新）
- 自訂 Scalar Types
- Field-level 權限控制
- 查詢複雜度限制
- 錯誤處理標準化

### 階段三：效能優化與整合
- 批次查詢優化
- 快取策略實作
- 前端 Houdini 整合
- GraphQL Playground 設置
- 效能監控與追蹤

## 交付項目

### 程式碼
- 完整的後端 API 原始碼
- 前端 SvelteKit 應用原始碼
- 單元測試與整合測試
- Docker Compose 設定檔

### 文件
- API 文件（自動生成 from GraphQL Schema）
- 開發者指南
- 資料庫 Schema 文件
- 架構設計文件

## 成功指標

### 功能完整性
- ✅ 所有 CRUD 功能正常運作
- ✅ 認證授權系統完整
- ✅ 即時功能運作（Subscriptions）
- ✅ 檔案上傳功能正常

### 品質指標
- 測試覆蓋率 > 80%
- 0 個高嚴重性 bug
- 程式碼通過 linting
- 文件完整度 > 90%

### 效能指標
- API 回應時間 p95 < 200ms
- 前端 FCP < 1.5s
- 資料庫查詢優化完成

## 風險與緩解

| 風險 | 影響 | 可能性 | 緩解策略 |
|------|------|--------|----------|
| GraphQL 查詢複雜度攻擊 | 高 | 中 | 實作查詢深度限制、複雜度計算 |
| N+1 查詢問題 | 高 | 高 | 使用 DataLoader 批次載入 |
| Schema 設計不當 | 高 | 中 | 遵循 GraphQL 最佳實踐、漸進式演進 |
| 過度獲取敏感資料 | 高 | 低 | Field-level 權限控制、資料遮罩 |

## MVP 版本規劃

### v1.0 核心功能
- **GraphQL API 完整實作**
  - Query：文章、用戶、標籤查詢
  - Mutation：CRUD 操作、認證、互動功能
  - Subscription：即時評論、新文章通知
- **GraphQL 特色展示**
  - DataLoader 批次載入
  - 計算欄位（isLiked, readTime）
  - 關聯資料解析
  - 查詢優化
- **開發工具整合**
  - GraphQL Playground
  - Schema 自動文件
  - 型別自動生成

## 技術債務管理

### 預期技術債
- 初期可能的效能瓶頸
- 測試覆蓋不足的部分
- 文件更新延遲

### 償還計畫
- 每個 Sprint 預留 20% 時間處理技術債
- 建立自動化測試逐步提高覆蓋率
- 使用文件生成工具減少手動維護

---

本文件為活文件，將隨專案進展持續更新。