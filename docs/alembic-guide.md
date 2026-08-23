# Alembic 資料庫遷移指南

## 環境說明

- **工作目錄**: 必須在 `backend/` 目錄下執行指令

## 常用指令

### 1. 檢查當前資料庫版本
```bash
cd backend
alembic current
```

### 2. 查看遷移歷史
```bash
cd backend
alembic history --verbose
```

### 3. 自動生成遷移檔案（當修改 Model 後）
```bash
cd backend
alembic revision --autogenerate -m "描述這次的變更"
```

例如：
```bash
# 新增欄位
alembic revision --autogenerate -m "Add avatar field to User model"

# 新增資料表
alembic revision --autogenerate -m "Add Tag model"

# 修改關聯
alembic revision --autogenerate -m "Add relationship between Post and Tag"
```

### 4. 執行遷移（升級到最新版本）
```bash
cd backend
alembic upgrade head
```

### 5. 升級到特定版本
```bash
cd backend
# 升級一個版本
alembic upgrade +1

# 升級到特定版本號
alembic upgrade ed3f497fe2d2
```

### 6. 降級資料庫版本
```bash
cd backend
# 降級一個版本
alembic downgrade -1

# 降級到特定版本
alembic downgrade ed3f497fe2d2

# 降級到初始狀態（清空所有遷移）
alembic downgrade base
```

### 7. 查看即將執行的 SQL（不實際執行）
```bash
cd backend
# 顯示升級的 SQL
alembic upgrade head --sql

# 顯示降級的 SQL
alembic downgrade -1 --sql
```

### 8. 手動創建遷移檔案（不自動偵測）
```bash
cd backend
alembic revision -m "Manual migration for custom changes"
```

## 工作流程範例

### 當你修改了 Model 後的標準流程：

1. **修改 Model 檔案**
   ```python
   # 例如在 app/models/user.py 新增欄位
   avatar_url = Column(String, nullable=True)
   ```

2. **生成遷移檔案**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add avatar field to User"
   ```

3. **檢查生成的遷移檔案**
   - 檔案位置: `backend/alembic/versions/`
   - 確認自動生成的內容是否正確

4. **執行遷移**
   ```bash
   alembic upgrade head
   ```

5. **驗證遷移結果**
   ```bash
   alembic current
   ```

## 重要注意事項

### 1. Model 檔案必須被 import
確保新的 Model 檔案在 `alembic/env.py` 中被 import：
```python
# 在 alembic/env.py 中
from app.models import user, post, comment, tag, like, follow  # Import all models
```

⚠️ **每次新增 Model 都必須在這裡補上 import**。Model 不會透過關聯「自動載入」——
`relationship()` 用的是字串名稱、`TYPE_CHECKING` 的 import 在執行期也不會生效。
若遺漏 import，該 model 就不在 `target_metadata` 中，autogenerate 會誤以為
資料庫中對應的表「應該被刪除」而生成 `drop_table`（本專案舊 migration 鏈
曾因此損壞，已於重建時修復）。

### 2. 資料庫連線設定
- 開發環境使用 `.env` 檔案設定（`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`）
- `alembic/env.py` 會從 settings 讀取配置並組合成 `postgresql+asyncpg://` URL
- 預設值定義在 `alembic.ini`，但會被 `env.py` 動態覆蓋

### 3. 遷移檔案版本控制
- 所有 `alembic/versions/*.py` 檔案都應該加入 git
- 團隊協作時注意遷移檔案的合併衝突

### 4. 資料庫重置（開發環境）
如果需要完全重置資料庫：
```bash
# 降級到初始狀態
cd backend
alembic downgrade base

# 升級到最新
alembic upgrade head
```

## 常見問題解決

### Q1: ModuleNotFoundError

**問題**:

執行 alembic 時出現模組找不到錯誤

**解決**:

確保在 backend 目錄下執行，並使用正確的 Python 環境

### Q2: 資料庫連線失敗

**問題**:

無法連接到資料庫

**解決**:

1. 確認 PostgreSQL 服務運行中: `docker compose up -d`
2. 檢查 `.env` 檔案的資料庫連線設定

### Q3: 自動偵測沒有找到變更

**問題**:

明明修改了 Model 但 autogenerate 說沒有變更

**解決**:

1. 確認 Model 檔案有在 `alembic/env.py` 中 import
2. 檢查是否有未提交的資料庫事務
3. 確認 Model 的 `__tablename__` 設定正確

### Q4: 遷移衝突

**問題**:

多個開發者同時創建遷移檔案導致衝突

**解決**:

```bash
# 先降級到共同版本
alembic downgrade [共同版本號]

# 合併遷移檔案後重新升級
alembic upgrade head
```

## 快速參考卡片

| 操作 | 指令 |
|-----|------|
| 查看當前版本 | `alembic current` |
| 自動生成遷移 | `alembic revision --autogenerate -m "message"` |
| 執行所有遷移 | `alembic upgrade head` |
| 回退一個版本 | `alembic downgrade -1` |
| 查看歷史 | `alembic history` |
| 重置資料庫 | `alembic downgrade base && alembic upgrade head` |

---

> 💡 **提示**: 建議在每次修改 Model 後立即生成並執行遷移，避免累積太多變更導致自動偵測出錯。
