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
- 評論通知
- 熱門文章排行

#### 6. 內容增強
- 圖片上傳 (文章封面)
- 程式碼高亮
- 閱讀時間估算
- 目錄自動生成

#### 7. AI 功能 (pgvector)
- 語義搜尋
- 相似文章推薦
- 自動標籤建議
- 重複內容檢測

## 技術架構

### 後端架構

#### Python 3.13 特性運用
- 更好的錯誤訊息
- 改進的 typing
- 更快的 CPython

#### 資料模型

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

class PostStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

@dataclass
class User:
    id: UUID
    email: str
    username: str
    password_hash: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = None

@dataclass
class Post:
    id: UUID
    title: str
    slug: str
    content: str  # Markdown format
    excerpt: str
    author_id: UUID
    status: PostStatus
    tags: List['Tag']
    created_at: datetime
    updated_at: datetime
    embedding: Optional[List[float]] = None  # vector(768) for Phase 2

@dataclass
class Comment:
    id: UUID
    content: str
    author_id: UUID
    post_id: UUID
    created_at: datetime

@dataclass
class Like:
    user_id: UUID
    post_id: UUID
    created_at: datetime

@dataclass
class Tag:
    id: UUID
    name: str
    slug: str
    created_at: datetime

@dataclass
class Follow:
    follower_id: UUID
    following_id: UUID
    created_at: datetime
```

### GraphQL Schema

```graphql
type Query {
  # 文章查詢
  posts(
    page: Int = 1
    limit: Int = 10
    tag: String
    authorId: ID
  ): PostConnection!

  post(id: ID, slug: String): Post

  # 用戶查詢
  me: User
  user(id: ID, username: String): User
  users(page: Int = 1, limit: Int = 10): UserConnection!

  # 搜尋
  search(
    query: String!
    type: SearchType = ALL
    semantic: Boolean = false
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
  # 即時通知
  commentAdded(postId: ID!): Comment!
  postPublished(authorId: ID): Post!
  notificationReceived: Notification!
}

type Post {
  id: ID!
  title: String!
  slug: String!
  content: String!
  excerpt: String!
  author: User!
  status: PostStatus!
  tags: [Tag!]!
  likes: Int!
  isLiked: Boolean!
  comments: [Comment!]!
  createdAt: DateTime!
  updatedAt: DateTime!
  readTime: Int!
  similarPosts(limit: Int = 5): [Post!]!  # Phase 2
}

type User {
  id: ID!
  email: String!
  username: String!
  bio: String
  avatarUrl: String
  posts(page: Int = 1, limit: Int = 10): PostConnection!
  followers: [User!]!
  following: [User!]!
  isFollowing: Boolean!
  createdAt: DateTime!
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

### 前端架構 (Svelte 5)

#### 使用 Svelte 5 新特性
- `$state` rune 進行狀態管理
- `$derived` rune 進行計算屬性
- `$effect` rune 處理副作用
- `$props` rune 處理組件屬性

#### 路由結構
```
src/routes/
├── +layout.svelte          # 全站布局
├── +page.svelte           # 首頁（文章列表）
├── +error.svelte          # 錯誤頁面
├── (auth)/
│   ├── login/
│   │   └── +page.svelte   # 登入頁面
│   └── register/
│       └── +page.svelte   # 註冊頁面
├── posts/
│   ├── +page.svelte       # 文章列表
│   ├── [slug]/
│   │   ├── +page.svelte   # 文章詳情
│   │   └── +page.ts       # 資料載入
│   ├── new/
│   │   └── +page.svelte   # 新增文章
│   └── edit/[id]/
│       └── +page.svelte   # 編輯文章
├── profile/
│   ├── +page.svelte       # 個人資料
│   └── [username]/
│       └── +page.svelte   # 用戶公開頁面
├── search/
│   └── +page.svelte       # 搜尋頁面
└── api/
    └── upload/
        └── +server.ts     # 檔案上傳端點
```

#### 組件結構
```
src/lib/components/
├── common/
│   ├── Header.svelte
│   ├── Footer.svelte
│   ├── Loading.svelte
│   └── ErrorMessage.svelte
├── posts/
│   ├── PostCard.svelte
│   ├── PostList.svelte
│   ├── PostEditor.svelte
│   └── PostContent.svelte
├── comments/
│   ├── CommentList.svelte
│   ├── CommentForm.svelte
│   └── CommentItem.svelte
├── user/
│   ├── UserCard.svelte
│   ├── UserAvatar.svelte
│   └── FollowButton.svelte
└── ui/
    ├── Button.svelte
    ├── Input.svelte
    ├── Modal.svelte
    └── Toast.svelte
```

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

### Sprint 1: 基礎設置 (Week 1)
- [ ] 專案架構初始化
- [ ] 資料庫設計與建立
- [ ] GraphQL Schema 定義
- [ ] 基本 CRUD API 實作
- [ ] 開發環境設定（Docker Compose）

### Sprint 2: 核心功能 (Week 2)
- [ ] 用戶認證系統（註冊/登入/JWT）
- [ ] 文章管理功能（CRUD）
- [ ] 評論系統實作
- [ ] 標籤系統
- [ ] 基礎權限控制

### Sprint 3: 前端整合 (Week 3)
- [ ] SvelteKit 專案設置
- [ ] Houdini 配置與整合
- [ ] 頁面路由實作
- [ ] 表單處理與驗證
- [ ] 狀態管理（Svelte stores）

### Sprint 4: 增強功能 (Week 4)
- [ ] 檔案上傳功能
- [ ] Markdown 編輯器與渲染
- [ ] 搜尋功能實作
- [ ] 分頁與無限滾動
- [ ] 社交功能（追蹤系統）

### Sprint 5: 進階功能 (Week 5)
- [ ] pgvector 整合設置
- [ ] 語義搜尋實作
- [ ] 文章推薦系統
- [ ] 效能優化（DataLoader）

### Sprint 6: 完善 (Week 6)
- [ ] 測試撰寫（覆蓋率 > 80%）
- [ ] 文件撰寫
- [ ] 效能調優

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
| Svelte 5 文件不足 | 高 | 中 | 提供詳細範例程式碼，建立社群支援 |
| Python 3.13 相容性問題 | 中 | 低 | 準備 Python 3.12 降級方案 |
| pgvector 學習曲線陡峭 | 中 | 高 | 設為選修內容，提供簡化的封裝 |
| Houdini 設定複雜 | 低 | 中 | 提供自動化設定腳本 |

## 版本規劃

### v1.0 - MVP (Month 1)
- 基礎 CRUD 功能
- 用戶認證
- 文章與評論
- 基本搜尋

### v1.5 - 社交功能 (Month 2)
- 追蹤系統
- 通知功能
- 進階搜尋
- 效能優化

### v2.0 - AI 功能 (Month 3)
- pgvector 整合
- 語義搜尋
- 智慧推薦
- 自動標籤

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