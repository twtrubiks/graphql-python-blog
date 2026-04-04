# GraphQL Blog Platform

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green.svg)](https://fastapi.tiangolo.com/)
[![Strawberry GraphQL](https://img.shields.io/badge/Strawberry_GraphQL-0.312-red.svg)](https://strawberry.rocks/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-orange.svg)](https://www.sqlalchemy.org/)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2.56-orange.svg)](https://svelte.dev/)
[![Svelte](https://img.shields.io/badge/Svelte-5-red.svg)](https://svelte.dev/)
[![Houdini](https://img.shields.io/badge/Houdini-2.0--next.11-purple.svg)](https://houdinigraphql.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-blue.svg)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-blue.svg)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-7-purple.svg)](https://vite.dev/)
[![Node.js](https://img.shields.io/badge/Node.js-24+-green.svg)](https://nodejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-orange.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

本專案目標是透過 Claude 學習, GraphQL API 和 Python 後端,

練習 GraphQL-First TDD 開發方法的最佳實.

## 🎯 專案目標

建立一個功能完整的部落格平台，作為 GraphQL + Python 的教學範例，展示：
- GraphQL API 設計與實作
- Test-Driven Development (TDD) 實踐
- 現代化的前後端架構
- 向量搜尋與 AI 功能整合 (尚未實做)

## 🛠 技術棧

### 後端
- **Python 3.13** - 最新版 Python
- **FastAPI** - 現代化 Web 框架
- **Strawberry** - Python GraphQL 函式庫
  - 選擇理由：原生 Type Hints 支援、與 FastAPI 完美整合、簡潔的裝飾器語法
  - 相比 Graphene 更現代化、更 Pythonic、開發效率更高
- **SQLAlchemy 2.0** - ORM 與資料庫操作
- **PostgreSQL 18** - 主要資料庫
- **pgvector** - 向量搜尋擴充套件（進階功能）(尚未實做)

### 前端
- **SvelteKit 2.56+** - 全端框架
- **Svelte 5** - 使用最新的 Runes 系統
- **Houdini v2.0.0-next.11** - GraphQL 客戶端（完整支援 Svelte 5）
- **Tailwind CSS 4** - 樣式框架（CSS-first 設定）
- **Vite 7** - 建置工具

### 測試
- **pytest** - 測試框架
- **pytest-asyncio** - 異步測試支援
- **httpx** - API 測試客戶端

## 📋 專案文件

### 核心文件
| 文件 | 說明 | 用途 |
|------|------|------|
| [產品需求文件](./docs/prd.md) | 定義專案功能與需求 | 了解要做什麼 |
| [系統架構文件](./docs/architecture.md) | C4 模型架構圖與技術決策 | 了解怎麼做 |
| [任務清單](./docs/tasks.md) | 詳細的開發任務分解 | 追蹤執行進度 |

### 開發指南
| 文件 | 說明 | 用途 |
|------|------|------|
| [TDD 完整指南](./docs/tdd-guide.md) | 測試驅動開發實踐方法 | 學習 TDD 方法論 |
| [Alembic 指南](./docs/alembic-guide.md) | 資料庫遷移管理 | 管理資料庫版本 |

### GraphQL 專題
| 文件 | 說明 | 用途 |
|------|------|------|
| [DataLoader 實作](./docs/dataloader-implementation.md) | N+1 查詢問題解決方案 | 效能優化指南 |
| [Union Types 指南](./docs/union-types-guide.md) | GraphQL Union Types 完整說明 | 多型返回值處理 |
| [Fragment 指南](./docs/fragment-guide.md) | GraphQL Fragment 重用機制 | 減少重複查詢 |
| [權限控制指南](./docs/permissions-guide.md) | GraphQL 權限控制機制 | 實作授權與權限管理 |
| [Subscription 指南](./docs/subscription-guide.md) | GraphQL Subscription 即時通訊 | 實作 WebSocket 即時推播 |
| [Relay Connection Pattern](./docs/relay-connection-pattern.md) | 標準化分頁實作 | 實現游標分頁 |

### 參考資料
| 文件 | 說明 | 用途 |
|------|------|------|
| [GraphQL 介紹](./docs/graphql-intro.md) | GraphQL 基礎概念 | 入門學習 |
| [GraphQL vs REST](./docs/graphql-vs-rest.md) | API 設計比較 | 技術選型參考 |

### 專案模組文件
| 模組 | 文件連結 | 說明 |
|------|---------|------|
| 前端 | [Frontend README](./frontend/README.md) | SvelteKit + Houdini 前端專案 |
| 後端 | [Backend README](./backend/README.md) | FastAPI + Strawberry 後端專案 |

## 🚀 快速開始

### 環境需求

- Python 3.13+
- Node.js 24+
- Docker 和 Docker Compose

> **注意**：本專案為教學練習用途，`.env` 配置檔已包含在版本控制中，可直接使用。
> 如果要用於生產環境，請務必修改敏感資訊並將 `.env` 加入 `.gitignore`。

### 啟動

db `blog_db`

```bash
docker-compose up -d
```

後端

```bash
cd backend

# 設定你的環境
# 注意：.env 已包含在專案中（教學用途），可直接使用預設配置
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt # 如果要跑測試

# migrate
alembic upgrade head

# 在 debug 中會自動 init_db()
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 也可以使用 FastAPI CLI
# fastapi dev app/main.py
```

後端 API [http://localhost:8000](http://localhost:8000)

後端 API 文檔 [http://localhost:8000/docs](http://localhost:8000/docs)

GraphQL [http://localhost:8000/graphql](http://localhost:8000/graphql)

前端

```bash
cd frontend

npm install

# 確保後端已經運行, 目的是要產生 schema.graphql
npm run codegen:pull

npm run dev
```

前端入口 [http://localhost:5173](http://localhost:5173)

### 生成資料

會使用 db `blog_db`

```bash
cd backend

# 創建測試用戶和文章
python3 ../scripts/seed-data.py
```

## 測試執行

### 測試腳本

會使用 db `test_blog` (測試時會自動創建)

```bash
cd backend

# 執行所有測試（資料庫會自動創建）
pytest

=========== 284 passed in 116.89s (0:01:56) =======================

# 只執行 GraphQL 測試
pytest tests/graphql/

# 執行特定測試檔案
pytest tests/graphql/queries/test_post_queries.py

# 顯示覆蓋率
pytest --cov=app --cov-report=html

# 執行快速測試（跳過慢速測試）
pytest -m "not slow"
```

### 測試資料庫說明

測試資料庫 `test_blog` 會在執行 pytest 時自動創建和清理，無需手動設置。

### 測試標記

```python
@pytest.mark.slow  # 慢速測試（如整合測試）
@pytest.mark.unit  # 單元測試
@pytest.mark.integration  # 整合測試
@pytest.mark.graphql  # GraphQL API 測試
```

## 📁 專案結構

```
GraphQL/
├── backend/
│   ├── app/
│   │   ├── api/           # API 端點
│   │   ├── graphql/       # GraphQL schema 和 resolvers
│   │   │   ├── mutations/     # GraphQL mutations
│   │   │   ├── queries/       # GraphQL queries
│   │   │   ├── subscriptions/ # GraphQL subscriptions (WebSocket)
│   │   │   └── types/         # GraphQL 型別定義
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # 業務邏輯
│   │   ├── core/          # 核心設定
│   │   └── utils/         # 工具函數
│   ├── tests/             # 測試檔案
│   ├── alembic/           # 資料庫遷移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/        # SvelteKit 路由
│   │   │   ├── posts/        # 文章頁面
│   │   │   ├── following/     # 追蹤動態
│   │   │   ├── my-drafts/     # 草稿管理
│   │   │   ├── my-posts/      # 我的文章
│   │   │   ├── profile/       # 個人資料
│   │   │   ├── settings/      # 個人設定
│   │   │   ├── search/        # 搜尋
│   │   │   └── users/         # 用戶頁面
│   │   ├── lib/           # 共用元件
│   │   └── $houdini/      # GraphQL 生成檔案
│   └── package.json
├── docker-compose.yml
└── docs/                  # 專案文件
    ├── prd.md
    ├── architecture.md
    ├── tasks.md
    └── ...
```

## 開發流程

本專案採用 **GraphQL-First TDD** 開發方法：

1. **寫測試**：先寫 GraphQL API 測試
2. **實作功能**：實作 resolver 讓測試通過
3. **重構**：優化程式碼保持測試綠燈
4. **文件**：更新相關文件

## 核心功能

### ✅ 已實現功能

**後端 (90%+ 完成)**
- ✅ 完整的 GraphQL API (Query, Mutation, Subscription)
- ✅ JWT 認證授權系統
- ✅ 文章 CRUD 操作
- ✅ 評論系統（即時推送）
- ✅ 按讚和追蹤功能
- ✅ 標籤和搜尋系統
- ✅ DataLoader 優化（解決 N+1）
- ✅ WebSocket 即時通訊
- ✅ 完整的測試覆蓋 (284 測試, 76% 覆蓋率)

**前端 (75%+ 完成)**
- ✅ SvelteKit + Houdini 整合
- ✅ 用戶註冊和登入
- ✅ 文章瀏覽和發布
- ✅ 即時評論更新
- ✅ Svelte 5 Runes 響應式系統
- ✅ 用戶個人資料與追蹤系統
- ✅ 個人設定頁面
- ✅ 草稿管理與快速發布
- ✅ 追蹤動態即時更新
- ✅ 在線狀態顯示

### GraphQL API 範例

完整的 API 查詢範例請參考：[GraphQL 範例文檔](./docs/graphql-examples.md)

```graphql
# 查詢文章列表
query GetPosts {
  posts(limit: 10, status: PUBLISHED) {
    edges {
      node {
        id
        title
        author {
          username
        }
        likesCount
        commentsCount
      }
    }
  }
}

# 即時訂閱評論
subscription OnCommentAdded($postId: ID!) {
  commentAdded(postId: $postId) {
    id
    content
    author {
      username
    }
  }
}
```

## 系統畫面

GraphQL Playground

![](https://cdn.imgpile.com/f/4HsNeyL_xl.png)

*互動式 GraphQL 查詢介面，支援即時文檔探索和查詢測試*

前端頁面

![](https://cdn.imgpile.com/f/D4UXJKz_xl.png)

![](https://cdn.imgpile.com/f/kpKS9CI_xl.png)

![](https://cdn.imgpile.com/f/geMcZOL_xl.png)

## Donation

文章都是我自己研究內化後原創，如果有幫助到您，也想鼓勵我的話，歡迎請我喝一杯咖啡 :laughing:

綠界科技ECPAY ( 不需註冊會員 )

![alt tag](https://payment.ecpay.com.tw/Upload/QRCode/201906/QRCode_672351b8-5ab3-42dd-9c7c-c24c3e6a10a0.png)

[贊助者付款](http://bit.ly/2F7Jrha)

歐付寶 ( 需註冊會員 )

![alt tag](https://i.imgur.com/LRct9xa.png)

[贊助者付款](https://payment.opay.tw/Broadcaster/Donate/9E47FDEF85ABE383A0F5FC6A218606F8)

## 贊助名單

[贊助名單](https://github.com/twtrubiks/Thank-you-for-donate)