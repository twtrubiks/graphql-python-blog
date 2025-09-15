# GraphQL Blog Platform 🚀

一個現代化的部落格平台，使用 GraphQL API 和 Python 後端，展示 GraphQL-First TDD 開發方法的最佳實踐。

graphql-python-blog

## 🎯 專案目標

建立一個功能完整的部落格平台，作為 GraphQL + Python 的教學範例，展示：
- GraphQL API 設計與實作
- Test-Driven Development (TDD) 實踐
- 現代化的前後端架構
- 向量搜尋與 AI 功能整合

## 🛠 技術棧

### 後端
- **Python 3.13** - 最新版 Python
- **FastAPI** - 現代化 Web 框架
- **Strawberry** - Python GraphQL 函式庫
- **SQLAlchemy 2.0** - ORM 與資料庫操作
- **PostgreSQL 16** - 主要資料庫
- **pgvector** - 向量搜尋擴充套件（進階功能）

### 前端
- **SvelteKit 2.x** - 全端框架
- **Svelte 5** - 使用最新的 Runes 系統
- **Houdini** - GraphQL 客戶端
- **Tailwind CSS** - 樣式框架

### 測試
- **pytest** - 測試框架
- **pytest-asyncio** - 異步測試支援
- **httpx** - API 測試客戶端
- **factory-boy** - 測試資料工廠

## 📋 專案文件

完整的專案文件幫助你了解和開發：

| 文件 | 說明 | 用途 |
|------|------|------|
| [產品需求文件](./docs/prd.md) | 定義專案功能與需求 | 了解要做什麼 |
| [系統架構文件](./docs/architecture.md) | C4 模型架構圖與技術決策 | 了解怎麼做 |
| [任務清單](./docs/tasks.md) | 詳細的開發任務分解 | 追蹤執行進度 |
| [測試策略](./docs/testing-strategy.md) | GraphQL-First TDD 方法論 | 了解如何測試 |
| [測試範例](./docs/tests-examples.md) | 完整的測試程式碼範例 | 參考實作方式 |
| [DataLoader 實作](./docs/dataloader-implementation.md) | N+1 查詢問題解決方案 | 效能優化指南 |

## 🚀 快速開始

### 環境需求

- Python 3.13+
- Node.js 22+
- Docker Compose (建立 PostgreSQL 16)

### 執行專案

**後端啟動**
```bash
# 開發模式
fastapi dev app/main.py

```

**前端啟動**
```bash
cd frontend
npm run dev
```

**Docker Compose 一鍵啟動**
```bash
docker-compose up
```

訪問：
- GraphQL Playground: http://localhost:8000/graphql
- 前端應用: http://localhost:5173

## 🧪 測試執行

### 執行所有測試
```bash
pytest
```

### 執行特定測試
```bash
# GraphQL API 測試
pytest tests/graphql/

# 服務層測試
pytest tests/services/

# 整合測試
pytest tests/integration/
```

### 測試覆蓋率
```bash
pytest --cov=app --cov-report=html
# 開啟 htmlcov/index.html 查看報告
```

## 📁 專案結構

```
GraphQL/
├── backend/
│   ├── app/
│   │   ├── api/           # API 端點
│   │   ├── graphql/       # GraphQL schema 和 resolvers
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
│   │   ├── lib/           # 共用元件
│   │   └── $houdini/      # GraphQL 生成檔案
│   └── package.json
├── docker-compose.yml
└── docs/                  # 專案文件
    ├── prd.md
    ├── architecture.md
    ├── tasks.md
    ├── testing-strategy.md
    └── tests-examples.md
```

## 🔄 開發流程

本專案採用 **GraphQL-First TDD** 開發方法：

1. **寫測試**：先寫 GraphQL API 測試
2. **實作功能**：實作 resolver 讓測試通過
3. **重構**：優化程式碼保持測試綠燈
4. **文件**：更新相關文件

### 提交訊息規範

使用 Conventional Commits：
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文件更新
- `test:` 測試相關
- `refactor:` 重構
- `chore:` 維護任務

## 📊 專案進度

查看 [tasks.md](./docs/tasks.md) 了解詳細進度：

- [ ] Sprint 1: 環境與基礎設置
- [ ] Sprint 2: 認證 API 開發
- [ ] Sprint 3: 文章查詢 API
- [ ] Sprint 4: 文章變更 API
- [ ] Sprint 5: 互動功能 API
- [ ] Sprint 6: 進階功能與即時通訊
- [ ] Sprint 7: 服務層實作
- [ ] Sprint 8: 整合測試
- [ ] Sprint 9: pgvector 整合
- [ ] Sprint 10: 前端整合

## 🤝 貢獻指南

歡迎貢獻！請遵循以下步驟：

1. Fork 專案
2. 創建功能分支
3. 提交變更（遵循提交規範）
4. 推送到分支
5. 開啟 Pull Request

### 程式碼規範

**Python**
```bash
# 格式化
black .
ruff check .

# 型別檢查
mypy app/
```

**JavaScript/TypeScript**
```bash
# 格式化
npm run format

# Lint
npm run lint
```

## 📈 效能指標

目標效能指標：
- GraphQL 查詢回應 < 200ms
- 首頁載入時間 < 2s
- Lighthouse 分數 > 90
- 測試覆蓋率：
  - GraphQL Resolvers > 95%
  - Service Layer > 90%
  - 整體測試覆蓋率 > 80%

## ⚙️ 環境變數設定

創建 `.env` 檔案並設定以下變數：

```bash
# 資料庫
DATABASE_URL=postgresql://user:pass@localhost/blog_db

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15

# 快取層 (選用 - 可使用 Redis 或其他方案)
# CACHE_URL=redis://localhost:6379

# 前端
PUBLIC_GRAPHQL_ENDPOINT=http://localhost:8000/graphql
```

## 📝 授權

MIT License - 詳見 [LICENSE](./LICENSE) 檔案

## 🙏 致謝

- FastAPI 和 Strawberry 團隊
- SvelteKit 和 Houdini 團隊
- 所有貢獻者

## 📞 聯絡方式

- 專案 Issues: [GitHub Issues](https://github.com/yourusername/graphql-blog/issues)
- Email: your-email@example.com

---

**Happy Coding! 🎉**

本專案是 GraphQL + Python 的完整教學範例，展示現代化 Web 開發的最佳實踐。