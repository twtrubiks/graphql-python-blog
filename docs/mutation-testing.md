# 變異測試（Mutation Testing）

> 對象：`backend/app/`（後端所有應用程式碼）
> 工具：`backend/mutation/`（本專案客製的變異測試執行器，原因見下文）

## 什麼是變異測試？

Code coverage 只能告訴你「哪些程式碼被執行過」，但**執行過不代表有被驗證**。

變異測試的做法是：故意在原始碼裡製造一個小錯誤（稱為**變異體 mutant**），例如把 `==` 改成 `!=`、把 `and_` 改成 `or_`、把 `await session.commit()` 刪掉，然後重跑測試：

| 結果 | 意義 |
|------|------|
| 測試失敗 → **killed（被殺死）** | 好事，測試抓到了這個錯誤 |
| 測試仍然通過 → **survived（存活）** | 測試沒能發現這個錯誤，代表測試有盲點 |
| 沒有測試執行到 → **no coverage** | 這段程式碼完全沒被測試 |

**變異分數 = 被殺死數 / (被殺死數 + 存活數)**，衡量的是測試的「斷言強度」，比 coverage 更接近「測試到底能不能抓到 bug」。

---

## 執行方式

```bash
docker compose up -d                    # 在專案根目錄啟動 PostgreSQL（同一般測試）
cd backend
pip install -r requirements-test.txt

python mutation/runner.py all                        # 產生 -> 建 worker -> coverage 對照 -> 執行 -> 報告（4 核心約 30 分鐘）
python mutation/runner.py report survived services   # 列出 services/ 下存活的變異體
python mutation/runner.py verify <ID>                # 單獨重跑某個變異體，看 pytest 輸出
```

分步驟執行、與先前的結果比較等指令，以及工具的設計細節，見 `backend/mutation/runner.py` 開頭的說明。所有中間產物都寫在 `backend/mutation/.cache/`（已加入 `.gitignore`）。

## 為什麼自製工具？

Python 最常用的 [mutmut](https://github.com/boxed/mutmut) 不適合本專案：

1. **mutmut 會跳過帶 decorator 的函式**（只放行 `@staticmethod` / `@classmethod`）。本專案大部分的 resolver 都掛著 `@strawberry.field` / `@strawberry.mutation` / `@strawberry.subscription`，用 mutmut 等於大半個 GraphQL 層都不會被測。
2. mutmut 以多個子行程平行執行，但 `conftest.py` 會 `DROP DATABASE` 再重建測試資料庫，**平行執行會互相砍掉資料庫**。

自製的執行器除了 `==`↔`!=`、`and`↔`or`、刪掉陳述式、`return None` 這類通用變異，還加入本專案特有的變異：

- **SQLAlchemy**：`and_`↔`or_`、`.is_()`↔`.is_not()`、`.in_()`→`.not_in()`、`.ilike()`→`.like()`，例如把軟刪除的過濾條件反過來
- **GraphQL**：`permission_classes=[IsAuthenticated]` → `[]`，拿掉權限守衛

完整的變異運算子見 `backend/mutation/mutgen.py`。

---

## 存活的變異體怎麼處理

存活不一定代表要補測試，要逐一判斷：

| 情況 | 處理方式 |
|------|------|
| 改壞後行為確實不同，只是沒有測試發現 | 補測試或加強斷言 |
| 程式碼本身多餘：死碼、呼叫端都會明確傳入的參數預設值、多餘的 `refresh` | 刪掉或簡化，變異體跟著消失 |
| 改了之後行為完全相同（**等價變異**），任何測試都不可能殺死 | 確認後忽略 |

例如以下是等價變異：

- 拿掉 `permission_classes=[IsAuthenticated]`：resolver 內部還會呼叫 `require_auth()`，錯誤訊息完全相同，屬於雙重防護
- 留言的 `deletedAt` 改成回傳 `None`：所有查詢都會排除已刪除的留言，API 拿到的值一定是 `null`。要消除它只能從 schema 移除這個欄位，屬於破壞性改動

判定為等價之前，先試著想出能區分兩者的情境。本專案曾把按讚查詢的 `==` → `!=` 誤判為等價：改成 `!=` 後會把別人對同一篇的讚誤判為「已經按讚過」，只是當時沒有測試涵蓋這個情境。

---

## 常見的測試盲點

以下是本專案跑變異測試時找到的問題，整理成通用的模式。

### 1. 沒有斷言，或斷言包在 `if` 裡

```python
if "errors" not in data and data["data"]["user"]:
    assert user_data["username"] == "otheruser"
    # 註解寫了「非擁有者不能看到 email」，卻沒有 assert email is None
```

條件不成立時什麼都不驗。email 的隱私權限整個拿掉，測試照樣通過。

### 2. 「出錯也算過」與關鍵字比對

```python
assert "errors" in data or data["data"]["followUser"]["success"] is False
assert "登入" in message or "authentication" in message
```

第一種只要程式炸掉就會通過。第二種曾經碰巧通過：拿掉留言的未登入檢查後，請求一路執行到 INSERT 才失敗，錯誤訊息裡的 SQL 參數是留言內容「未登入評論」，剛好含有「登入」。錯誤訊息要完整比對。

### 3. 測試環境與正式環境不一致

測試用的資料庫 session 曾在每個請求結束時自動 commit，正式環境卻只 close 不 commit：resolver 漏寫 `commit()` 時測試全綠，上線後資料卻沒有寫入。測試的 session 也曾少了正式環境的 `autoflush=False`，掩蓋了「同一篇文章帶 slug 相同的標籤時會重複建立」的 bug。測試要盡量共用正式環境的設定。

### 4. 只檢查回傳值，沒有重新查詢

mutation 的回傳值來自同一個 session，即使沒有 commit 也看得到變更。unfollow / unlike 只檢查 `success: true`，刪掉 `session.delete()` 也不會失敗。寫入類的操作要用新的請求查回來驗證。

### 5. 假物件讓查詢條件失去意義

假的 session 不管查詢條件是什麼都回傳同一個使用者，`User.id == user_id` 改成 `!=` 也測不出來。驗證查詢條件時要用真的資料庫，並準備「不該被查到」的資料。

### 6. 清理與副作用沒有驗證

- 訂閱的 `finally: unsubscribe(...)` 被刪掉，佇列會無限累積；要在 generator `aclose()` 之後斷言訂閱者已清空
- mutation 觸發的推播（新留言、通知追蹤者）在背景執行，從回傳值看不出來；要實際訂閱並等待事件，失敗的情境也要確認沒有推播

### 7. 邊界值

`len(password) < 8` 改成 `<= 8`，只有剛好 8 個字元的測試抓得到。分頁的最後一頁、excerpt 的長度上限、查詢深度限制都是同樣的道理。

### 8. 輸出相同的退化

DataLoader 失效時會改走逐筆查詢的 fallback，結果完全相同，只是 SQL 次數變多（N+1）。這類問題只能直接數 SQL：例如取 1 篇和 5 篇文章的查詢次數應該相同。
