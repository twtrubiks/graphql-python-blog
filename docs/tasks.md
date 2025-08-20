# GraphQL 部落格平台 - 任務清單

> 本專案採用 **GraphQL-First TDD** 開發方法，將 GraphQL API 測試作為主要重點，每個測試都是可執行的 API 文件。

## 📋 任務總覽

- [環境設置](#環境設置)
- [測試環境設置](#測試環境設置)
- [GraphQL API 開發 (主要重點)](#graphql-api-開發-主要重點)
- [服務層開發](#服務層開發)
- [整合測試](#整合測試)
- [進階功能](#進階功能)
- [前端整合](#前端整合)
- [文件任務](#文件任務)

---

## 環境設置

### 基礎環境
- [ ] 安裝 Python 3.13
- [ ] 設置虛擬環境 (venv/poetry)
- [ ] 安裝 PostgreSQL 16
- [ ] 設置快取層 (選用 - 可使用 Redis 或其他方案)
- [ ] 創建專案目錄結構

### 後端環境
- [ ] 初始化 Python 專案
- [ ] 安裝核心套件 (FastAPI, Strawberry, SQLAlchemy)
- [ ] 設置環境變數檔案 (.env)
- [ ] 配置 Docker Compose 開發環境
- [ ] 設置資料庫連線

### 前端環境
- [ ] 安裝 Node.js 22+
- [ ] 創建 SvelteKit 專案 (使用 Svelte 5)
- [ ] 安裝 Houdini
- [ ] 設置開發伺服器

---

## 測試環境設置

### 測試框架設置
- [ ] 安裝 pytest 及相關套件
  ```bash
  pytest>=7.4.0
  pytest-asyncio>=0.21.0
  pytest-cov>=4.1.0
  httpx>=0.24.0
  factory-boy>=3.3.0
  faker>=19.0.0
  freezegun>=1.2.0
  ```
- [ ] 創建 pytest.ini 配置檔
- [ ] 設置測試資料庫
- [ ] 創建測試目錄結構
  ```
  tests/
  ├── conftest.py
  ├── factories.py
  ├── graphql/
  │   ├── queries/
  │   ├── mutations/
  │   └── subscriptions/
  ├── services/
  └── integration/
  ```

### 測試工具準備
- [ ] 創建測試客戶端 fixture (auth/non-auth)
- [ ] 創建 GraphQL 查詢常數檔
- [ ] 創建資料工廠 (UserFactory, PostFactory, etc.)
- [ ] 設置測試資料隔離機制 (transaction rollback)
- [ ] 設置測試覆蓋率目標 (整體 80%, GraphQL 95%)

---

## GraphQL API 開發 (主要重點)

> 🎯 **70% 的測試重點在這裡** - 每個測試都展示實際的 GraphQL 操作

### Sprint 1: 環境與基礎設置

#### 1. GraphQL Schema 設置
- [ ] 創建 Strawberry schema
- [ ] 設置 FastAPI 整合
- [ ] 配置 GraphQL playground
- [ ] 設置 CORS 與安全性

### Sprint 2: 認證 API 開發

#### 2. 認證 Mutations (GraphQL-First TDD)
- [ ] 📝 測試：註冊 mutation 完整流程
  ```graphql
  mutation Register($email: String!, $password: String!, $username: String!) {
    register(email: $email, password: $password, username: $username) {
      user { id, email, username }
      token
    }
  }
  ```
- [ ] 實作：register mutation resolver
- [ ] 📝 測試：登入 mutation 與 JWT 生成
- [ ] 實作：login mutation resolver
- [ ] 📝 測試：refresh token mutation
- [ ] 實作：refreshToken mutation resolver
- [ ] 📝 測試：錯誤處理（重複 email、弱密碼等）
- [ ] 實作：驗證邏輯與錯誤回應

### Sprint 3: 文章查詢 API

#### 3. 文章查詢 (GraphQL-First TDD)
- [ ] 📝 測試：查詢已發布文章列表
  ```graphql
  query GetPosts($page: Int!, $limit: Int!) {
    posts(page: $page, limit: $limit) {
      edges {
        node { id, title, excerpt, author { username } }
      }
      pageInfo { hasNextPage, totalCount }
    }
  }
  ```
- [ ] 實作：posts query resolver 與分頁
- [ ] 📝 測試：單一文章查詢（含巢狀資料）
- [ ] 實作：post query resolver
- [ ] 📝 測試：標籤過濾查詢
- [ ] 實作：過濾邏輯
- [ ] 📝 測試：作者文章查詢
- [ ] 實作：user.posts field resolver

### Sprint 4: 文章變更 API

#### 4. 文章操作 (GraphQL-First TDD)
- [ ] 📝 測試：創建文章 mutation（需認證）
  ```graphql
  mutation CreatePost($input: PostInput!) {
    createPost(input: $input) {
      id, title, slug, status
    }
  }
  ```
- [ ] 實作：createPost mutation（含權限檢查）
- [ ] 📝 測試：更新文章 mutation（只有作者可編輯）
- [ ] 實作：updatePost mutation
- [ ] 📝 測試：刪除文章 mutation
- [ ] 實作：deletePost mutation
- [ ] 📝 測試：發布/取消發布文章
- [ ] 實作：publishPost/unpublishPost mutations

### Sprint 5: 互動功能 API

#### 5. 評論系統 (GraphQL-First TDD)
- [ ] 📝 測試：新增評論 mutation
- [ ] 實作：createComment mutation
- [ ] 📝 測試：查詢文章評論（巢狀查詢）
- [ ] 實作：post.comments field resolver
- [ ] 📝 測試：刪除評論（權限檢查）
- [ ] 實作：deleteComment mutation

#### 6. 按讚功能 (GraphQL-First TDD)
- [ ] 📝 測試：按讚/取消按讚 mutation
- [ ] 實作：likePost/unlikePost mutations
- [ ] 📝 測試：查詢按讚狀態與數量
- [ ] 實作：post.likes, post.isLiked field resolvers

### Sprint 6: 進階功能與即時通訊

#### 7. 搜尋功能 (GraphQL-First TDD)
- [ ] 📝 測試：全文搜尋 query
  ```graphql
  query Search($query: String!, $type: SearchType) {
    search(query: $query, type: $type) {
      ... on Post { id, title, excerpt }
      ... on User { id, username, bio }
    }
  }
  ```
- [ ] 實作：search query resolver
- [ ] 📝 測試：複雜過濾與排序
- [ ] 實作：進階查詢邏輯

#### 8. DataLoader 優化 (GraphQL-First TDD)
- [ ] 📝 測試：N+1 查詢問題驗證
- [ ] 實作：User DataLoader
- [ ] 📝 測試：批次載入效能
- [ ] 實作：Comment DataLoader

#### 9. Subscriptions (GraphQL-First TDD)
- [ ] 📝 測試：WebSocket 連線建立
- [ ] 實作：WebSocket endpoint
- [ ] 📝 測試：新評論即時通知
  ```graphql
  subscription OnCommentAdded($postId: ID!) {
    commentAdded(postId: $postId) {
      id, content, author { username }
    }
  }
  ```
- [ ] 實作：commentAdded subscription
- [ ] 📝 測試：文章發布通知
- [ ] 實作：postPublished subscription

---

## 服務層開發

> 🎯 **20% 的測試重點** - 專注於業務邏輯驗證

### Sprint 7: 服務層實作

#### 10. 基礎模型與資料庫
- [ ] 創建 SQLAlchemy models (User, Post, Comment, Tag, Like, Follow)
- [ ] 設置 Alembic migrations
- [ ] 創建資料庫連線池
- [ ] 實作基礎 Repository pattern

#### 11. 認證服務
- [ ] 📝 測試：密碼加密與驗證
- [ ] 實作：Password hashing (bcrypt)
- [ ] 📝 測試：JWT token 生成與驗證
- [ ] 實作：JWT service
- [ ] 📝 測試：Token refresh 機制
- [ ] 實作：Refresh token logic

#### 12. 業務邏輯服務
- [ ] 📝 測試：只有作者可以編輯文章
- [ ] 實作：Post ownership validation
- [ ] 📝 測試：草稿狀態轉換規則
- [ ] 實作：Post status management
- [ ] 📝 測試：評論權限控制
- [ ] 實作：Comment permission service

#### 13. 檔案處理服務
- [ ] 📝 測試：圖片大小與格式驗證
- [ ] 實作：File validation service
- [ ] 📝 測試：檔案儲存路徑生成
- [ ] 實作：Storage service (local/S3)

---

## 整合測試

> 🎯 **10% 的測試重點** - 端到端關鍵流程驗證

### Sprint 8: 整合測試

#### 14. 完整發布流程
- [ ] 📝 測試：註冊 → 登入 → 創建草稿 → 編輯 → 發布
- [ ] 📝 測試：發布後的評論與互動流程
- [ ] 📝 測試：作者管理自己的文章

#### 15. 社交互動流程
- [ ] 📝 測試：追蹤作者 → 接收通知 → 查看動態
- [ ] 📝 測試：多用戶評論與討論串

#### 16. 搜尋與發現流程
- [ ] 📝 測試：搜尋 → 過濾 → 排序 → 分頁
- [ ] 📝 測試：相關文章推薦流程

---

## 進階功能

### Sprint 9: pgvector 整合

#### 17. 向量資料庫設置
- [ ] 安裝 pgvector extension
- [ ] 📝 測試：向量欄位儲存與查詢
- [ ] 實作：Vector column migration
- [ ] 設置向量索引 (IVFFlat)

#### 18. Embedding 服務
- [ ] 📝 測試：文字轉向量 (使用 sentence-transformers)
- [ ] 實作：Embedding generation service
- [ ] 📝 測試：批次向量生成
- [ ] 實作：Async batch processing

#### 19. 語義搜尋 API
- [ ] 📝 測試：相似文章查詢
  ```graphql
  query SimilarPosts($postId: ID!) {
    post(id: $postId) {
      similarPosts(limit: 5) {
        id, title, similarity
      }
    }
  }
  ```
- [ ] 實作：Similarity search resolver
- [ ] 📝 測試：混合搜尋（關鍵字 + 語義）
- [ ] 實作：Hybrid search logic

---

## 前端整合

### Sprint 10: 前端基礎

#### 20. SvelteKit 設置
- [ ] 創建 SvelteKit 專案 (Svelte 5)
- [ ] 設置 TypeScript
- [ ] 配置 Tailwind CSS
- [ ] 設置環境變數

#### 21. Houdini 整合
- [ ] 安裝 Houdini
- [ ] 配置 GraphQL endpoint
- [ ] 生成 TypeScript types
- [ ] 創建基礎查詢

#### 22. 頁面實作
- [ ] 實作首頁（文章列表）
- [ ] 實作文章詳情頁
- [ ] 實作登入/註冊頁
- [ ] 實作個人資料頁
- [ ] 實作文章編輯器

#### 23. 狀態管理
- [ ] 實作認證 store (Svelte 5 $state)
- [ ] 實作用戶 store
- [ ] 實作通知系統
- [ ] 實作錯誤處理

---

## 文件任務

### 技術文件
- [ ] 撰寫 API 文件 (自動生成 from GraphQL)
- [ ] 撰寫測試策略文件
- [ ] 撰寫開發者指南
- [ ] 撰寫架構決策記錄 (ADR)

### 教學文件
- [ ] 撰寫 GraphQL + Python 基礎教學
- [ ] 撰寫 GraphQL-First TDD 實踐教學
- [ ] 撰寫 Strawberry 深入教學
- [ ] 撰寫 SvelteKit + Houdini 整合教學
- [ ] 撰寫 pgvector 語義搜尋教學

### 範例與練習
- [ ] 創建每個 GraphQL 操作的範例
- [ ] 設計漸進式練習題目
- [ ] 撰寫詳細解答與說明
- [ ] 準備 Workshop 投影片與材料

---

## 測試優先級與分配

### 測試分配比例
- 📊 **GraphQL API Tests**: 70%
- 🔧 **Service Layer Tests**: 20%
- 🔄 **Integration Tests**: 10%

### 關鍵測試指標
- GraphQL Resolvers 覆蓋率: > 95%
- Service Layer 覆蓋率: > 90%
- 整體測試覆蓋率: > 80%

## GraphQL-First TDD 執行原則

1. **測試先行**：每個 GraphQL 操作都先寫測試
2. **測試即文件**：測試展示實際的 API 使用方式
3. **漸進開發**：紅燈 → 綠燈 → 重構循環

## 測試命名規範

### GraphQL API 測試
```python
def test_<operation>_<resource>_<scenario>():
    """
    測試案例：<中文描述>
    GraphQL 操作：<query/mutation name>
    """
```

### Service 層測試
```python
def test_<service>_<action>_<expected_result>():
    """測試：<業務規則描述>"""
```

## 任務統計

- **總任務數**: ~120 項
- **GraphQL API 任務**: ~50 項 (42%)
- **服務層任務**: ~25 項 (21%)
- **前端任務**: ~20 項 (17%)
- **文件任務**: ~15 項 (12%)
- **其他**: ~10 項 (8%)

## 標記說明

- 📝 **GraphQL 測試任務**：需要先寫測試的 GraphQL API 功能
- 📊 **效能相關**：需要考慮效能優化
- 🔧 **技術實作**：純技術實作任務
- 📚 **文件任務**：文件撰寫相關

---

> 💡 **核心理念**：專注於 GraphQL API 測試，每個測試都是可執行的 API 範例！

本文件將隨專案進展持續更新，確保所有任務的可追蹤性。