# GraphQL 部落格平台 - 測試策略

## 核心理念：GraphQL-First TDD

本專案採用 **GraphQL-First TDD** 測試策略，將 GraphQL API 測試作為主要重點，因為：
1. 測試直接展示 GraphQL 操作方式
2. 每個測試都是可執行的 API 文件
3. 學生學到的是實際會用到的技能

## 測試金字塔

```
         Integration Tests (10%)
               端到端流程
              ／        ＼
             ／          ＼
        Service Tests (20%)
           業務邏輯驗證
          ／            ＼
         ／              ＼
    GraphQL API Tests (70%)
        主要測試重點
```

## 測試目錄結構

```
tests/
├── conftest.py                 # 全域 fixtures
├── factories.py                # 測試資料工廠
├── graphql/                    # GraphQL API 測試 (主要)
│   ├── queries/
│   │   ├── test_post_queries.py
│   │   ├── test_user_queries.py
│   │   └── test_search_queries.py
│   ├── mutations/
│   │   ├── test_auth_mutations.py
│   │   ├── test_post_mutations.py
│   │   └── test_comment_mutations.py
│   └── subscriptions/
│       └── test_subscriptions.py
├── services/                   # 服務層測試
│   ├── test_auth_service.py
│   ├── test_post_service.py
│   └── test_vector_service.py
├── models/                     # 模型測試
│   └── test_models.py
└── integration/                # 整合測試
    ├── test_user_journey.py
    └── test_publishing_flow.py
```

## GraphQL API 測試 (70%)

### 測試原則

1. **測試即文件**：每個測試展示一個 GraphQL 操作
2. **完整性**：包含請求和回應的完整結構
3. **實用性**：測試案例可直接用於前端開發參考

### 測試結構

```python
class TestPostQueries:
    """
    Feature: 文章查詢功能
    作為一個讀者，我想要瀏覽和搜尋文章
    """
    
    @pytest.mark.asyncio
    async def test_get_published_posts_with_pagination(self, client):
        """
        測試案例：查詢已發布文章列表（含分頁）
        GraphQL 操作：posts query with pagination
        """
        # Arrange: 準備測試資料
        await PostFactory.create_batch(15, status="published")
        
        # GraphQL Query（這就是前端會用的）
        query = """
            query GetPosts($page: Int!, $limit: Int!) {
                posts(page: $page, limit: $limit) {
                    edges {
                        node {
                            id
                            title
                            excerpt
                            author {
                                username
                                avatarUrl
                            }
                            tags {
                                name
                            }
                            createdAt
                        }
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        totalCount
                    }
                }
            }
        """
        
        # Act: 執行 GraphQL 請求
        response = await client.post("/graphql", json={
            "query": query,
            "variables": {
                "page": 1,
                "limit": 10
            }
        })
        
        # Assert: 驗證回應
        assert response.status_code == 200
        data = response.json()["data"]["posts"]
        assert len(data["edges"]) == 10
        assert data["pageInfo"]["hasNextPage"] is True
        assert data["pageInfo"]["totalCount"] == 15
        
        # 驗證資料結構
        first_post = data["edges"][0]["node"]
        assert "id" in first_post
        assert "author" in first_post
        assert "tags" in first_post
```

### 測試分類

#### 1. Query 測試
- 單一資源查詢
- 列表查詢與分頁
- 複雜巢狀查詢
- 過濾與排序
- 搜尋功能

#### 2. Mutation 測試
- 資源創建
- 資源更新
- 資源刪除
- 批次操作
- 檔案上傳

#### 3. Subscription 測試
- 連線建立
- 事件接收
- 斷線重連

#### 4. 錯誤處理測試
- 驗證錯誤
- 權限錯誤
- 業務邏輯錯誤
- 系統錯誤

## Service 層測試 (20%)

### 測試重點

專注於業務邏輯，不涉及 GraphQL：

```python
class TestPostService:
    """文章服務業務邏輯測試"""
    
    @pytest.mark.asyncio
    async def test_only_author_can_edit_post(self):
        """測試：只有作者可以編輯文章"""
        # Given: 一篇文章和兩個用戶
        author = await UserFactory.create()
        other_user = await UserFactory.create()
        post = await PostFactory.create(author=author)
        
        # When & Then: 非作者編輯應該拋出錯誤
        with pytest.raises(PermissionError):
            await PostService.update_post(
                post_id=post.id,
                user_id=other_user.id,
                data={"title": "Hacked Title"}
            )
```

### 測試範圍

- 權限檢查邏輯
- 資料驗證規則
- 業務流程控制
- 第三方服務整合

## Integration 測試 (10%)

### 測試重點

端到端的關鍵用戶流程：

```python
class TestPublishingJourney:
    """完整的文章發布流程測試"""
    
    @pytest.mark.asyncio
    async def test_complete_publishing_workflow(self, client):
        """
        測試案例：從註冊到發布文章的完整流程
        User Journey: 新用戶 → 註冊 → 登入 → 創建草稿 → 發布文章
        """
        # Step 1: 註冊新用戶
        register_response = await client.post("/graphql", json={
            "query": REGISTER_MUTATION,
            "variables": {
                "email": "writer@example.com",
                "password": "SecurePass123",
                "username": "newwriter"
            }
        })
        token = register_response.json()["data"]["register"]["token"]
        
        # Step 2: 使用 token 創建草稿
        client.headers["Authorization"] = f"Bearer {token}"
        draft_response = await client.post("/graphql", json={
            "query": CREATE_POST_MUTATION,
            "variables": {
                "input": {
                    "title": "My First Post",
                    "content": "This is my story...",
                    "status": "DRAFT"
                }
            }
        })
        post_id = draft_response.json()["data"]["createPost"]["id"]
        
        # Step 3: 發布文章
        publish_response = await client.post("/graphql", json={
            "query": PUBLISH_POST_MUTATION,
            "variables": {"id": post_id}
        })
        
        # Verify: 文章已發布且可公開訪問
        assert publish_response.json()["data"]["publishPost"]["status"] == "PUBLISHED"
```

## 測試工具與設置

### 必要套件

```python
# requirements-test.txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0           # 測試 async FastAPI
factory-boy>=3.3.0      # 測試資料工廠
faker>=19.0.0           # 假資料生成
freezegun>=1.2.0        # 時間控制
```

### Fixtures 設計

```python
# conftest.py
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client():
    """未認證的測試客戶端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_client(client):
    """已認證的測試客戶端"""
    # 創建測試用戶並登入
    user = await UserFactory.create()
    token = generate_token(user)
    client.headers["Authorization"] = f"Bearer {token}"
    return client

@pytest.fixture
async def db_session():
    """測試資料庫 session"""
    async with async_session() as session:
        yield session
        await session.rollback()
```

### 測試資料工廠

```python
# factories.py
import factory
from factory import fuzzy

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    password = "TestPass123"
    
    @classmethod
    async def create(cls, **kwargs):
        """異步創建用戶"""
        user = cls.build(**kwargs)
        user.password_hash = hash_password(user.password)
        async with async_session() as session:
            session.add(user)
            await session.commit()
        return user

class PostFactory(factory.Factory):
    class Meta:
        model = Post
    
    title = factory.Faker("sentence", nb_words=5)
    content = factory.Faker("text", max_nb_chars=1000)
    excerpt = factory.Faker("text", max_nb_chars=200)
    status = "published"
    author = factory.SubFactory(UserFactory)
```

## 測試命名規範

### GraphQL API 測試

```python
def test_<operation>_<resource>_<condition>_<expected_result>():
    """
    測試案例：<中文描述>
    GraphQL 操作：<query/mutation/subscription 名稱>
    """
    pass

# 範例
def test_query_posts_with_tag_filter_returns_filtered_results():
    """
    測試案例：使用標籤過濾查詢文章
    GraphQL 操作：posts query with tag parameter
    """
```

### Service 層測試

```python
def test_<action>_<condition>_<result>():
    """測試：<業務規則描述>"""
    pass

# 範例
def test_create_post_with_duplicate_slug_raises_error():
    """測試：重複的 slug 應該拋出錯誤"""
```

## 測試執行策略

### 本地開發

```bash
# 執行所有測試
pytest

# 只執行 GraphQL 測試
pytest tests/graphql/

# 執行特定測試檔案
pytest tests/graphql/queries/test_post_queries.py

# 顯示覆蓋率
pytest --cov=app --cov-report=html

# 執行快速測試（跳過慢速測試）
pytest -m "not slow"
```

### 測試標記

```python
@pytest.mark.slow  # 慢速測試（如整合測試）
@pytest.mark.unit  # 單元測試
@pytest.mark.integration  # 整合測試
@pytest.mark.graphql  # GraphQL API 測試
```

## 覆蓋率目標

- **整體覆蓋率**: 80%+
- **GraphQL Resolvers**: 95%+
- **Service 層**: 90%+
- **Models**: 70%+
- **Utilities**: 60%+

## 測試最佳實踐

### 1. 測試獨立性
每個測試應該獨立執行，不依賴其他測試的結果

### 2. 測試資料隔離
使用 transaction rollback 確保測試間資料隔離

### 3. 明確的斷言
```python
# 好的斷言
assert response.status_code == 200
assert data["posts"]["totalCount"] == 5

# 不好的斷言
assert response.ok
assert data
```

### 4. 測試錯誤情況
不只測試成功路徑，也要測試錯誤處理

### 5. 使用有意義的測試資料
```python
# 好的測試資料
title = "GraphQL 入門教學"

# 不好的測試資料
title = "test123"
```

## 持續改進

### 測試報告
- 每次 commit 執行測試
- 產生覆蓋率報告
- 追蹤測試趨勢

### 測試維護
- 定期重構測試程式碼
- 更新過時的測試案例
- 移除重複的測試

### 效能監控
- 標記慢速測試
- 優化測試執行時間
- 平行執行測試

---

本測試策略確保程式碼品質的同時，也提供了豐富的 GraphQL API 使用範例，讓測試成為最好的文件。