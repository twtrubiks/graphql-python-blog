# Test-Driven Development (TDD) 完整指南

## 目錄
- [什麼是 TDD？](#什麼是-tdd)
- [TDD 的核心循環](#tdd-的核心循環)
- [為什麼要使用 TDD？](#為什麼要使用-tdd)
- [TDD 的實踐步驟](#tdd-的實踐步驟)
- [實際案例演示](#實際案例演示)
- [常見的錯誤與迷思](#常見的錯誤與迷思)
- [TDD 最佳實踐](#tdd-最佳實踐)
- [相關文檔](#相關文檔)

## 什麼是 TDD？

**測試驅動開發 (Test-Driven Development, TDD)** 是一種軟體開發方法論，核心概念是：

> 先寫測試，再寫程式碼

這聽起來違反直覺，但它能幫助你：
- **明確需求**：寫測試時就必須思考功能的預期行為
- **聚焦目標**：只寫剛好讓測試通過的程式碼
- **建立安全網**：有測試保護，重構時更有信心
- **創建文檔**：測試本身就是最好的使用範例

## TDD 的核心循環

TDD 遵循一個簡單但強大的循環，稱為 **紅-綠-重構 (Red-Green-Refactor)**：

```
     ┌─────────────┐
     │   1. RED    │
     │  寫測試失敗  │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │  2. GREEN   │
     │ 寫程式碼通過 │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │ 3. REFACTOR │
     │   重構優化   │
     └──────┬──────┘
            │
            └──────► (重複循環)
```

### 1. 紅燈階段 (Red) 🔴
- **寫一個失敗的測試**
- 定義功能的預期行為
- 測試必須失敗（因為功能還沒實作）
- 這確保測試本身是有效的

### 2. 綠燈階段 (Green) 🟢
- **寫最少的程式碼讓測試通過**
- 不要過度設計
- 目標是快速通過測試
- 可以先寫"醜"的程式碼

### 3. 重構階段 (Refactor) 🔄
- **在測試保護下改善程式碼**
- 優化程式碼結構
- 消除重複
- 改善可讀性
- 測試必須持續通過

## 為什麼要使用 TDD？

### 優點 ✅

1. **更好的程式碼設計**
   - 強迫你思考介面設計
   - 程式碼自然具有高內聚、低耦合
   - 更容易測試的程式碼通常也是更好的程式碼

2. **減少 Bug**
   - 及早發現問題
   - 邊界條件都被測試覆蓋
   - 回歸測試自動化

3. **活的文檔**
   - 測試展示如何使用程式碼
   - 永遠是最新的（否則測試會失敗）
   - 新人容易理解系統行為

4. **重構信心**
   - 有完整測試覆蓋
   - 改壞了馬上知道
   - 可以大膽優化

5. **開發節奏**
   - 小步前進，持續回饋
   - 明確的完成定義
   - 減少除錯時間

### 挑戰 ⚠️

1. **學習曲線**
   - 需要改變思維模式
   - 初期可能會變慢

2. **測試維護**
   - 測試也需要維護
   - 不好的測試會成為負擔

3. **不是萬能藥**
   - 不能取代其他測試（整合測試、E2E 測試）
   - 某些情況不適用（UI 原型、探索性程式設計）

## TDD 的實踐步驟

### Step 1: 分析需求
在寫任何程式碼前，先思考：
- 這個功能要解決什麼問題？
- 輸入和輸出是什麼？
- 有哪些邊界條件？
- 錯誤情況如何處理？

### Step 2: 寫測試案例
從最簡單的案例開始：
```python
def test_功能描述_情境_預期結果():
    # Arrange (準備)
    # Act (執行)
    # Assert (斷言)
```

### Step 3: 執行測試看它失敗
```bash
pytest test_feature.py  # 應該要失敗 ❌
```

### Step 4: 實作功能
寫最少的程式碼通過測試：
```python
def feature():
    return expected_result  # 最簡單的實作
```

### Step 5: 執行測試看它通過
```bash
pytest test_feature.py  # 應該要通過 ✅
```

### Step 6: 重構（如果需要）
在綠燈狀態下改善程式碼

### Step 7: 重複循環
加入更多測試案例，逐步完善功能

## 實際案例演示

讓我們用本專案的 **user query** 功能作為範例：

### 1. 紅燈：先寫測試 🔴

```python
# tests/graphql/test_auth_queries.py
class TestUserQuery:
    """測試 user query (查詢單一用戶)"""

    @pytest.mark.asyncio
    async def test_user_query_by_id(self, client: AsyncClient, test_session: AsyncSession):
        """測試根據 ID 查詢單一用戶"""
        # Arrange: 準備測試資料
        user = User(
            email="queryuser@example.com",
            username="queryuser",
            hashed_password=AuthService.get_password_hash("Password123!"),
            bio="Test user bio"
        )
        test_session.add(user)
        await test_session.commit()

        # Act: 執行 GraphQL 查詢
        query = """
            query GetUser($userId: Int!) {
                user(id: $userId) {
                    id
                    email
                    username
                    bio
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"userId": user.id}
            }
        )

        # Assert: 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["user"]["email"] == "queryuser@example.com"
```

執行測試：
```bash
pytest test_auth_queries.py::TestUserQuery::test_user_query_by_id
# 失敗！因為 user query 還沒實作 ❌
```

### 2. 綠燈：實作功能 🟢

```python
# app/graphql/queries/user.py
async def get_user(
    info: Info,
    id: Optional[int] = None,
    username: Optional[str] = None
) -> Optional[UserType]:
    """查詢單一用戶"""
    if not id and not username:
        return None

    db = info.context["db_session"]
    query = select(User)

    if id:
        query = query.where(User.id == id)
    elif username:
        query = query.where(User.username == username)

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return UserType.from_orm(user)
```

```python
# app/graphql/schema.py
@strawberry.type
class Query:
    user: Optional[UserType] = strawberry.field(resolver=get_user)
```

執行測試：
```bash
pytest test_auth_queries.py::TestUserQuery::test_user_query_by_id
# 通過！✅
```

### 3. 重構：優化程式碼 🔄

在測試保護下，我們可以安心重構：
- 抽取共用邏輯
- 改善命名
- 優化查詢效能
- 加入快取機制

每次修改後執行測試，確保功能正常。

### 4. 加入更多測試案例

```python
async def test_user_query_nonexistent_user(self, client: AsyncClient):
    """測試查詢不存在的用戶"""
    # 應該返回 null

async def test_user_query_inactive_user(self, client: AsyncClient):
    """測試查詢停用的用戶"""
    # 應該返回用戶但 isActive 為 False

async def test_user_query_without_sensitive_data(self, client: AsyncClient):
    """測試不應返回敏感資料"""
    # 確保沒有密碼欄位
```

## 常見的錯誤與迷思

### ❌ 錯誤 1：寫太多程式碼
```python
# 不好：過度設計
def get_user():
    # 實作快取
    # 實作日誌
    # 實作權限檢查
    # ... 100 行程式碼
```

```python
# 好：只通過當前測試
def get_user():
    return user  # 簡單直接
```

### ❌ 錯誤 2：測試太複雜
```python
# 不好：一個測試測太多東西
def test_user_system():
    # 測試註冊
    # 測試登入
    # 測試查詢
    # 測試更新
    # 測試刪除
```

```python
# 好：一個測試一個概念
def test_user_query_by_id():
    # 只測試根據 ID 查詢
```

### ❌ 錯誤 3：測試實作細節
```python
# 不好：測試內部實作
def test_user_query():
    assert user._internal_method() == "something"
```

```python
# 好：測試行為
def test_user_query():
    assert user.email == "test@example.com"
```

### ❌ 迷思 1：TDD 會讓開發變慢
- 短期可能變慢，長期反而更快
- 減少除錯時間
- 減少 bug 修復時間

### ❌ 迷思 2：要 100% 測試覆蓋率
- 追求有意義的測試，不是數字
- 某些程式碼不需要測試（如簡單的 getter/setter）

### ❌ 迷思 3：TDD 適用所有情況
- UI 原型可能不適合
- 探索性程式設計時可以先不用
- 第三方整合可能需要不同策略

## TDD 最佳實踐

### 1. 保持測試簡單快速 ⚡
```python
# 好的測試
def test_add():
    assert add(2, 3) == 5  # 簡單明瞭
```

### 2. 測試命名要清楚 📝
```python
# 模式：test_<功能>_<情境>_<預期結果>
def test_login_with_invalid_password_returns_error():
    pass
```

### 3. 遵循 AAA 模式 🎯
```python
def test_feature():
    # Arrange（準備）
    data = prepare_test_data()

    # Act（執行）
    result = execute_feature(data)

    # Assert（斷言）
    assert result == expected
```

### 4. 一次只測一件事 1️⃣
```python
# 不好
def test_user():
    assert user.name == "John"
    assert user.age == 30
    assert user.email == "john@example.com"

# 好
def test_user_name():
    assert user.name == "John"

def test_user_age():
    assert user.age == 30
```

### 5. 測試邊界條件 🔍
```python
def test_empty_input():
    assert function("") == None

def test_null_input():
    assert function(None) == None

def test_maximum_input():
    assert function("x" * 1000) == expected
```

### 6. 使用測試替身 🎭
```python
# Mock 外部依賴
@patch('external.api.call')
def test_with_mock(mock_api):
    mock_api.return_value = {"status": "ok"}
    result = my_function()
    assert result == expected
```

### 7. 保持測試獨立 🏝️
```python
# 每個測試應該能獨立執行
def test_a():
    # 不依賴 test_b 的結果
    pass

def test_b():
    # 不依賴 test_a 的結果
    pass
```

## GraphQL-First TDD

在本專案中，我們採用 **GraphQL-First TDD** 方法：

### 特點
1. **以 GraphQL 操作為中心**：測試直接使用 GraphQL queries/mutations
2. **測試即文檔**：每個測試展示實際的 API 使用方式
3. **端到端驗證**：從 GraphQL 層測試到資料庫

### 範例
```python
class TestPostMutations:
    @pytest.mark.asyncio
    async def test_create_post_mutation(self, auth_client):
        """測試：創建文章 mutation"""
        mutation = """
            mutation CreatePost($input: PostInput!) {
                createPost(input: $input) {
                    id
                    title
                    content
                    author {
                        username
                    }
                }
            }
        """

        response = await auth_client.post("/graphql", json={
            "query": mutation,
            "variables": {
                "input": {
                    "title": "TDD 實踐指南",
                    "content": "TDD 是一種開發方法..."
                }
            }
        })

        assert response.status_code == 200
        data = response.json()["data"]["createPost"]
        assert data["title"] == "TDD 實踐指南"
```

## 相關文檔

### 本專案相關文檔
- [測試策略](./testing-strategy.md) - 本專案的完整測試策略與 GraphQL-First TDD 說明
- [測試範例](./tests-examples.md) - 完整的測試程式碼範例
- [專案架構](./architecture.md) - 包含可測試性設計原則
- [任務清單](./tasks.md) - 展示 TDD 開發流程的實際應用

### 外部資源
- [Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) - Kent Beck 的經典書籍
- [TDD Course by Uncle Bob](https://cleancoders.com/episode/clean-code-episode-6-p1) - Robert C. Martin 的 TDD 教學
- [Martin Fowler on TDD](https://martinfowler.com/bliki/TestDrivenDevelopment.html) - Martin Fowler 的 TDD 文章
- [Pytest Documentation](https://docs.pytest.org/) - Python 測試框架文檔

## 總結

TDD 不只是一種測試方法，更是一種設計方法。它幫助你：

1. **先思考再動手** - 明確需求和介面
2. **小步前進** - 降低複雜度
3. **持續回饋** - 快速發現問題
4. **安全重構** - 有測試保護
5. **活的文檔** - 測試展示用法

記住 TDD 的核心循環：

```
紅燈 🔴 → 綠燈 🟢 → 重構 🔄
```

開始可能不習慣，但一旦掌握，你會發現它讓開發更有節奏、更有信心。

> "The only way to go fast, is to go well." - Robert C. Martin

---
