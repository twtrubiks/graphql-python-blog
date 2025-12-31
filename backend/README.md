# GraphQL Blog Backend

使用 FastAPI + Strawberry GraphQL + PostgreSQL 建構的現代化部落格後端 API。

## 技術堆疊

- **Python 3.13** - 最新版 Python
- **FastAPI** - 高效能的現代化 Web 框架
- **Strawberry** - Python GraphQL 函式庫
- **SQLAlchemy 2.0** - ORM 與資料庫操作
- **PostgreSQL 18** - 主要資料庫
- **Alembic** - 資料庫遷移管理
- **JWT** - 身份驗證機制

## 專案結構

```
backend/
├── app/
│   ├── api/           # REST API 端點
│   ├── graphql/       # GraphQL（queries/mutations/subscriptions/types）
│   ├── models/        # SQLAlchemy 資料模型（User/Post/Comment/Tag/Like/Follow）
│   ├── services/      # 業務邏輯層
│   ├── core/          # 核心設定（config/database/security/deps）
│   └── main.py        # 應用程式入口
├── tests/             # 測試（graphql/services/models/integration）
├── alembic/           # 資料庫遷移
└── requirements.txt   # 專案依賴
```

## 功能完成度

| 項目 | 數量 | 測試覆蓋率 |
|------|------|-----------|
| Queries | 10+ | 76% |
| Mutations | 15 | 76% |
| Subscriptions | 5 | 100% |
| DataLoaders | 8 | 88% |
| 總測試數 | 284 | 全部通過 |

## 快速開始

### 環境需求

- Python 3.13+
- PostgreSQL 18
- Docker (可選，用於資料庫)

## GraphQL API

### GraphQL Playground

開發模式下可訪問 GraphQL Playground：
```
http://localhost:8000/graphql
```

### 主要功能

#### 查詢 (Queries)
- `posts` - 獲取文章列表（支援分頁、篩選）
- `post` - 獲取單篇文章（by ID 或 slug）
- `postsByTag` - 依單一標籤篩選文章
- `postsByTags` - 依多個標籤篩選文章
- `postsByAuthor` - 獲取特定作者的文章
- `followingPosts` - 獲取追蹤用戶的文章
- `user` - 獲取使用者資訊
- `me` - 獲取當前登入使用者
- `onlineUsers` - 獲取在線使用者列表
- `search` - 全文搜尋（Union Type：文章+用戶）
- `tags` - 獲取所有標籤列表

#### 變更 (Mutations)
**認證相關**
- `register` - 使用者註冊
- `login` - 使用者登入
- `updateMe` - 更新個人資料

**文章相關**
- `createPost` - 創建文章
- `updatePost` - 更新文章
- `deletePost` - 刪除文章
- `publishPost` - 發布草稿
- `unpublishPost` - 取消發布（轉為草稿）

**評論相關**
- `addComment` - 新增評論
- `updateComment` - 更新評論
- `deleteComment` - 刪除評論

**互動相關**
- `likePost` - 按讚文章
- `unlikePost` - 取消按讚
- `followUser` - 追蹤用戶
- `unfollowUser` - 取消追蹤

#### 訂閱 (Subscriptions)
- `commentAdded` - 新評論即時通知
- `postPublished` - 文章發布通知
- `followedUserPosted` - 追蹤用戶發文通知
- `postDeleted` - 文章刪除通知
- `userStatusChanged` - 使用者上線/離線狀態變更

### 認證機制

使用 JWT Token 進行身份驗證：

1. 透過 `login` mutation 獲取 token
2. 在請求 header 中加入：
```
Authorization: Bearer <your-token>
```

受保護的操作有兩種實作方式：

**方式一：在 Schema 定義時使用 permission_classes**
```python
# 在 schema.py 中定義
create_post: PostType = strawberry.field(
    resolver=create_post,
    permission_classes=[IsAuthenticated]  # 需要認證的使用者
)
```

**方式二：在 Resolver 內部檢查**
```python
# 在 resolver 函數中
async def create_post(info: Info, input: PostInput) -> PostType:
    current_user = await require_auth(info)  # 驗證並取得當前用戶
    # ... 執行創建文章邏輯
```

## 測試

### 執行所有測試
```bash
pytest
```

### 執行特定測試
```bash
# GraphQL 測試
pytest tests/graphql/

# 服務層測試
pytest tests/services/

# 整合測試
pytest tests/integration/
```

### 測試覆蓋率
```bash
pytest --cov=app --cov-report=html
```

## 資料庫管理

### 創建新的遷移
```bash
alembic revision --autogenerate -m "描述變更"
```

### 執行遷移
```bash
alembic upgrade head
```

### 回滾遷移
```bash
alembic downgrade -1
```

## DataLoader 優化

專案使用 DataLoader 模式解決 N+1 查詢問題（實作於 `app/graphql/dataloaders.py`）：

| DataLoader | 用途 |
|------------|------|
| `UserLoader` | 批次載入用戶資料 |
| `PostLoader` | 批次載入文章 |
| `CommentLoader` | 批次載入評論 |
| `PostCommentsLoader` | 批次載入文章的所有評論 |
| `LikeCountLoader` | 批次載入文章按讚數 |
| `UserLikedPostsLoader` | 批次載入用戶按讚的文章 |
| `FollowersCountLoader` | 批次載入追蹤者數量 |
| `FollowingCountLoader` | 批次載入追蹤中數量 |

詳細實作請參考 [DataLoader 實作指南](../docs/dataloader-implementation.md)

## 開發指南

### 新增 GraphQL Type

1. 在 `app/graphql/types/` 創建類型定義
2. 在 `app/graphql/schema.py` 註冊類型
3. 實作對應的 resolver

### 新增業務邏輯

1. 在 `app/services/` 創建服務類別
2. 實作業務邏輯方法
3. 在 GraphQL resolver 中調用服務

### 新增資料模型

1. 在 `app/models/` 創建 SQLAlchemy 模型
2. 創建 Alembic 遷移
3. 執行遷移更新資料庫

## 環境變數

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| DB_HOST | 資料庫主機 | localhost |
| DB_PORT | 資料庫連接埠 | 5432 |
| DB_USER | 資料庫用戶 | blog_user |
| DB_PASSWORD | 資料庫密碼 | blog_password |
| DB_NAME | 資料庫名稱 | blog_db |
| SECRET_KEY | JWT 密鑰 | - |
| ALGORITHM | JWT 算法 | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 過期時間（分鐘，預設 7 天） | 10080 |
| DEBUG | 除錯模式 | True |

## 相關文件

- [系統架構](../docs/architecture.md)
- [GraphQL 專題文件](../docs/)
- [API 文件](http://localhost:8000/docs) (FastAPI 自動生成)

## 注意事項

- 確保 PostgreSQL 服務正在運行
- 開發環境使用 `.env` 檔案，生產環境使用環境變數
- 定期更新依賴套件以修復安全漏洞
- 遵循 GraphQL-First TDD 開發流程