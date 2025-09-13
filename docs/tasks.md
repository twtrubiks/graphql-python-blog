# GraphQL 部落格平台 - 任務清單

> 本專案採用 **GraphQL-First TDD** 開發方法，優先完成後端所有功能與測試，再進行前端開發。
>
> **關於 TDD**：請參考 [TDD 完整指南](./tdd-guide.md) 了解測試驅動開發的概念與實踐方法。

## 📋 開發策略

- **後端優先**：完整實作所有 GraphQL API 與測試 (Phase 1-5)
- **測試驅動**：每個功能都先寫測試，再寫實作
- **前端最後**：後端完成後才開始前端開發 (Phase 6)

---

## Phase 1: 基礎環境設置 (Week 1)

### 1.1 專案結構建立
- [x] 創建 backend/ 目錄結構
  ```
  backend/
  ├── app/
  │   ├── api/           # API 端點
  │   ├── graphql/       # GraphQL schema 和 resolvers
  │   ├── models/        # SQLAlchemy models
  │   ├── services/      # 業務邏輯
  │   ├── core/          # 核心設定
  │   └── utils/         # 工具函數
  ├── tests/             # 測試檔案
  ├── alembic/           # 資料庫遷移
  └── requirements.txt
  ```

### 1.2 依賴套件設置
- [x] 創建 requirements.txt
  ```
  fastapi[standard]
  strawberry-graphql[fastapi]
  sqlalchemy
  asyncpg
  pydantic-settings
  python-jose[cryptography]
  passlib[bcrypt]
  #python-multipart==0.0.9
  alembic
  python-slugify
  ```
- [x] 創建 requirements-test.txt
  ```
  pytest
  pytest-asyncio
  pytest-cov

  factory-boy==3.3.0
  faker==26.0.0
  freezegun==1.5.0
  ```

### 1.3 FastAPI + Strawberry 整合
- [x] 創建 app/main.py - FastAPI 應用程式入口
- [x] 創建 app/core/config.py - 環境變數設定
- [x] 創建 app/graphql/schema.py - GraphQL schema 定義
- [x] 設置 GraphQL playground endpoint
- [x] 配置 CORS 設定

### 1.4 資料庫連線設置
- [x] 創建 app/core/database.py - SQLAlchemy 異步連線
- [x] 創建 app/models/base.py - SQLAlchemy Base 模型
- [x] 設置 Alembic 初始化
- [x] 創建 .env 檔案範本

### 1.5 測試環境準備
- [x] 創建測試目錄結構
  ```
  tests/
  ├── conftest.py         # pytest 配置與 fixtures
  ├── factories.py        # 測試資料工廠
  ├── graphql/
  │   ├── queries/
  │   ├── mutations/
  │   └── subscriptions/
  ├── services/
  └── integration/
  ```
- [x] 創建測試資料庫 fixture
- [x] 創建 GraphQL 測試客戶端
- [x] 設置測試事務回滾機制
- [x] 創建基礎測試常數檔

---

## Phase 2: 認證系統實作 (Week 2)

### 2.1 User 模型與資料庫
- [x] 實作：app/models/user.py - User SQLAlchemy 模型
- [x] 創建 User migration
- [x] 實作：app/services/auth.py - 密碼加密服務 (bcrypt)

### 2.2 註冊功能 (TDD)
- [x] 📝 測試：註冊 mutation 成功案例
  ```graphql
  mutation Register($email: String!, $password: String!, $username: String!) {
    register(email: $email, password: $password, username: $username) {
      user { id, email, username }
      token
    }
  }
  ```
- [x] 實作：register mutation resolver
- [x] 📝 測試：重複 email 錯誤處理
- [x] 📝 測試：重複 username 錯誤處理
- [x] 實作：輸入驗證與錯誤處理

### 2.3 登入功能 (TDD)
- [x] 📝 測試：登入 mutation 成功案例
  ```graphql
  mutation Login($email: String!, $password: String!) {
    login(email: $email, password: $password) {
      user { id, email, username }
      token
    }
  }
  ```
- [x] 實作：login mutation resolver
- [x] 📝 測試：錯誤密碼處理
- [x] 📝 測試：不存在用戶處理
- [x] 實作：JWT token 生成服務

### 2.4 簡單認證機制
- [x] 實作：JWT 驗證 middleware
- [x] 📝 測試：me query (取得當前用戶)
- [x] 實作：me query resolver
- [x] 📝 測試：認證保護的 query

### 2.5 用戶查詢
- [x] 📝 測試：user query (查詢單一用戶)
- [x] 實作：user query resolver
- [x] 📝 測試：users query (用戶列表)
- [x] 實作：users query resolver with pagination

---

## Phase 3: 文章管理核心功能 (Week 4-5)

### 3.1 Post 模型與關聯
- [x] 📝 測試：Post 模型驗證
- [x] 實作：app/models/post.py - Post SQLAlchemy 模型
- [x] 創建 Post migration
- [x] 📝 測試：User-Post 關聯
- [x] 實作：外鍵關聯設置

### 3.2 文章創建 (TDD)
- [x] 📝 測試：創建文章 mutation (需認證)
  ```graphql
  mutation CreatePost($input: PostInput!) {
    createPost(input: $input) {
      id
      title
      slug
      content
      status
      author { id, username }
    }
  }
  ```
- [x] 實作：createPost mutation resolver
- [x] 📝 測試：未認證用戶無法創建
- [x] 📝 測試：slug 自動生成
- [x] 📝 測試：草稿狀態管理
- [x] 實作：文章創建服務

### 3.3 文章查詢 (TDD)
- [x] 📝 測試：單一文章查詢
  ```graphql
  query GetPost($id: ID!) {
    post(id: $id) {
      id
      title
      content
      excerpt
      author { username, bio }
      createdAt
      updatedAt
    }
  }
  ```
- [x] 實作：post query resolver
- [x] 📝 測試：文章列表查詢與分頁
  ```graphql
  query GetPosts($page: Int!, $limit: Int!) {
    posts(page: $page, limit: $limit) {
      edges {
        node { id, title, excerpt, author { username } }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        totalCount
      }
    }
  }
  ```
- [x] 實作：posts query resolver with pagination
- [x] 📝 測試：只顯示已發布文章
- [x] 實作：文章狀態過濾

### 3.4 文章更新與刪除 (TDD)
- [x] 📝 測試：更新文章 mutation (只有作者可編輯)
  ```graphql
  mutation UpdatePost($id: ID!, $input: PostInput!) {
    updatePost(id: $id, input: $input) {
      id
      title
      content
      updatedAt
    }
  }
  ```
- [x] 實作：updatePost mutation resolver
- [x] 📝 測試：非作者無法編輯
- [x] 📝 測試：刪除文章 mutation
- [x] 實作：deletePost mutation resolver
- [x] 📝 測試：軟刪除機制
- [x] 實作：軟刪除邏輯

### 3.5 文章發布管理 (簡化版)
- [x] 📝 測試：發布文章 mutation
- [x] 實作：publishPost mutation
- [x] 📝 測試：取消發布 mutation
- [x] 實作：unpublishPost mutation

---

## Phase 4: 互動功能開發 (Week 6-7)

### 4.1 標籤系統
- [x] 📝 測試：Tag 模型與多對多關聯
- [x] 實作：app/models/tag.py - Tag 模型
- [x] 📝 測試：文章標籤查詢
- [x] 實作：post.tags field resolver
- [x] 📝 測試：標籤過濾查詢
- [x] 實作：posts query with tag filter

### 4.2 評論系統 (TDD)
- [x] 📝 測試：Comment 模型
- [x] 實作：app/models/comment.py
- [x] 📝 測試：新增評論 mutation
  ```graphql
  mutation AddComment($postId: ID!, $content: String!) {
    addComment(postId: $postId, content: $content) {
      id
      content
      author { username }
      createdAt
    }
  }
  ```
- [x] 實作：addComment mutation resolver
- [x] 📝 測試：查詢文章評論
- [x] 實作：post.comments field resolver
- [x] 📝 測試：刪除評論 (作者或文章作者可刪)
- [x] 實作：deleteComment mutation

### 4.3 按讚功能 (TDD)
- [ ] 📝 測試：Like 模型
- [ ] 實作：app/models/like.py
- [ ] 📝 測試：按讚 mutation
  ```graphql
  mutation LikePost($postId: ID!) {
    likePost(postId: $postId) {
      success
      post { likesCount, isLiked }
    }
  }
  ```
- [ ] 實作：likePost mutation
- [ ] 📝 測試：取消按讚 mutation
- [ ] 實作：unlikePost mutation
- [ ] 📝 測試：查詢按讚狀態
- [ ] 實作：post.isLiked, post.likesCount resolvers

### 4.4 追蹤功能 (TDD)
- [ ] 📝 測試：Follow 模型
- [ ] 實作：app/models/follow.py
- [ ] 📝 測試：追蹤用戶 mutation
- [ ] 實作：followUser mutation
- [ ] 📝 測試：取消追蹤 mutation
- [ ] 實作：unfollowUser mutation
- [ ] 📝 測試：查詢追蹤者/追蹤中
- [ ] 實作：user.followers, user.following resolvers

---

## Phase 5: 進階功能與優化 (Week 8-9)

### 5.1 搜尋功能
- [ ] 📝 測試：全文搜尋 query
  ```graphql
  query Search($query: String!, $type: SearchType) {
    search(query: $query, type: $type) {
      ... on Post { id, title, excerpt }
      ... on User { id, username, bio }
      ... on Tag { id, name, postsCount }
    }
  }
  ```
- [ ] 實作：PostgreSQL 全文搜尋
- [ ] 📝 測試：搜尋結果排序
- [ ] 實作：相關性排序算法

### 5.2 DataLoader 優化
- [ ] 📝 測試：N+1 查詢問題檢測
- [ ] 實作：User DataLoader
- [ ] 📝 測試：Post DataLoader
- [ ] 實作：Comment DataLoader
- [ ] 📝 測試：批次載入效能驗證
- [ ] 實作：Like/Follow DataLoader

### 5.3 Subscription 即時通訊
- [ ] 📝 測試：WebSocket 連線
- [ ] 實作：WebSocket endpoint 設置
- [ ] 📝 測試：新評論即時通知
  ```graphql
  subscription OnCommentAdded($postId: ID!) {
    commentAdded(postId: $postId) {
      id
      content
      author { username }
    }
  }
  ```
- [ ] 實作：commentAdded subscription
- [ ] 📝 測試：文章發布通知
- [ ] 實作：postPublished subscription

### 5.4 快取層實作 (選用 - 非教學重點)
- [ ] ~~Redis 連線設置~~ (暫不實作)
- [ ] ~~Redis 快取服務~~ (暫不實作)
- [ ] ~~查詢結果快取~~ (暫不實作)
- [ ] ~~GraphQL 查詢快取~~ (暫不實作)
- [ ] ~~快取失效策略~~ (暫不實作)
- [ ] ~~快取更新機制~~ (暫不實作)

### 5.5 檔案上傳 (簡化版)
- [ ] 📝 測試：圖片上傳 mutation
- [ ] 實作：uploadImage mutation
- [ ] 📝 測試：檔案大小與格式驗證
- [ ] 實作：本地檔案儲存服務

---

## Phase 6: 前端開發 (Week 10-12)

> 後端完成後才開始前端開發

### 6.1 SvelteKit 專案設置
- [ ] 創建 SvelteKit 專案 (Svelte 5)
- [ ] 設置 TypeScript
- [ ] 配置 Tailwind CSS
- [ ] 設置環境變數
- [ ] 配置 SSR/CSR 策略

### 6.2 Houdini GraphQL 整合
- [ ] 安裝並配置 Houdini
- [ ] 設置 GraphQL endpoint
- [ ] 生成 TypeScript types
- [ ] 創建基礎查詢與 mutations
- [ ] 設置認證 headers

### 6.3 認證流程頁面
- [ ] 實作登入頁面
- [ ] 實作註冊頁面
- [ ] 實作密碼重設頁面
- [ ] 實作認證 store (Svelte 5 $state)
- [ ] 實作路由守衛

### 6.4 文章相關頁面
- [ ] 實作首頁 (文章列表)
- [ ] 實作文章詳情頁
- [ ] 實作文章編輯器 (Markdown)
- [ ] 實作草稿管理頁面
- [ ] 實作標籤瀏覽頁面

### 6.5 用戶相關頁面
- [ ] 實作個人資料頁
- [ ] 實作個人設定頁
- [ ] 實作追蹤者/追蹤中列表
- [ ] 實作通知中心
- [ ] 實作用戶公開頁面

### 6.6 互動功能元件
- [ ] 實作評論元件
- [ ] 實作按讚按鈕
- [ ] 實作追蹤按鈕
- [ ] 實作分享功能
- [ ] 實作搜尋元件

### 6.7 GraphQL Subscriptions 整合
- [ ] 設置 WebSocket 連線到 GraphQL endpoint
- [ ] 實作 commentAdded subscription 監聽
- [ ] 實作 postPublished subscription 監聽
- [ ] UI 即時更新顯示

---

## 測試覆蓋率目標

### 後端測試覆蓋率
- **GraphQL Resolvers**: > 95%
- **Service Layer**: > 90%
- **Models**: > 85%
- **整體後端**: > 85%

### 測試類型分配
- **單元測試**: 60%
- **整合測試**: 30%
- **E2E 測試**: 10%

---

## 開發原則

1. **後端優先**: 所有後端功能必須完成並測試通過才開始前端
2. **TDD 嚴格執行**: 每個功能都必須先寫測試（詳見 [TDD 指南](./tdd-guide.md#tdd-的核心循環)）
3. **測試即文件**: 測試案例就是 API 使用範例
4. **漸進式開發**: 紅燈 → 綠燈 → 重構（詳見 [TDD 循環說明](./tdd-guide.md#tdd-的核心循環)）
5. **程式碼品質**: 每個 Sprint 結束前執行 linting 和 type checking

---

## 時程估計

- **Phase 1**: 1 週 (環境設置)
- **Phase 2**: 1 週 (認證系統 - 已簡化)
- **Phase 3**: 1.5 週 (文章管理 - 已簡化)
- **Phase 4**: 1.5 週 (互動功能 - 已簡化)
- **Phase 5**: 1.5 週 (進階功能 - 已簡化)
- **Phase 6**: 1.5 週 (前端開發 - 已簡化)

**總計**: 8 週完成整個專案

---

## 標記說明

- 📝 **測試優先**: 必須先寫測試的任務
- 🔧 **純實作**: 技術實作任務
- 📊 **效能相關**: 需要考慮效能的任務
- 🎨 **前端任務**: 前端相關開發

---

> 💡 **核心理念**: 後端是重點，必須有完整的測試覆蓋，前端是展示層，在後端穩定後才開始開發。

本文件將隨專案進展持續更新。