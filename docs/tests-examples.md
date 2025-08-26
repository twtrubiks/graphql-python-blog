# GraphQL 部落格平台 - 測試範例

本文件提供完整的測試範例程式碼，展示如何使用 GraphQL-First TDD 方法開發。每個範例都是可執行的 GraphQL 操作教學。

> **相關文檔**：
> - [TDD 完整指南](./tdd-guide.md) - 了解 TDD 的基本概念與實踐方法
> - [測試策略](./testing-strategy.md) - 本專案的測試架構設計

## 目錄

- [測試設置](#測試設置)
- [GraphQL Query 測試範例](#graphql-query-測試範例)
- [GraphQL Mutation 測試範例](#graphql-mutation-測試範例)
- [GraphQL Subscription 測試範例](#graphql-subscription-測試範例)
- [錯誤處理測試範例](#錯誤處理測試範例)
- [服務層測試範例](#服務層測試範例)
- [整合測試範例](#整合測試範例)

---

## 測試設置

### conftest.py - 全域 Fixtures

```python
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base
from app.auth import create_access_token
from tests.factories import UserFactory, PostFactory

# 測試資料庫設置
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost/test_blog",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    """Create a new database session for a test."""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client():
    """Create test client without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_client(client, db_session):
    """Create authenticated test client."""
    user = await UserFactory.create(db_session)
    token = create_access_token({"sub": str(user.id)})
    client.headers["Authorization"] = f"Bearer {token}"
    client.user = user  # Attach user for reference in tests
    return client
```

### factories.py - 測試資料工廠

```python
import factory
from factory import fuzzy
from datetime import datetime
import bcrypt

from app.models import User, Post, Comment, Tag

class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    async def create(session, **kwargs):
        defaults = {
            "email": factory.Faker("email").generate(),
            "username": factory.Faker("user_name").generate(),
            "password": "TestPassword123!",
            "bio": factory.Faker("text", max_nb_chars=200).generate(),
        }
        defaults.update(kwargs)

        # Hash password
        if "password" in defaults:
            password = defaults.pop("password")
            defaults["password_hash"] = bcrypt.hashpw(
                password.encode(), bcrypt.gensalt()
            ).decode()

        user = User(**defaults)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

class PostFactory:
    """Factory for creating test posts."""

    @staticmethod
    async def create(session, author=None, **kwargs):
        if not author:
            author = await UserFactory.create(session)

        defaults = {
            "title": factory.Faker("sentence", nb_words=5).generate(),
            "content": factory.Faker("text", max_nb_chars=1000).generate(),
            "excerpt": factory.Faker("text", max_nb_chars=200).generate(),
            "slug": factory.Faker("slug").generate(),
            "status": "published",
            "author_id": author.id,
            "created_at": datetime.utcnow(),
        }
        defaults.update(kwargs)

        post = Post(**defaults)
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post
```

---

## GraphQL Query 測試範例

### 測試：查詢文章列表（含分頁）

```python
# tests/graphql/queries/test_post_queries.py
import pytest
from tests.factories import PostFactory

class TestPostQueries:
    """
    Feature: 文章查詢功能
    作為讀者，我想要瀏覽文章列表並查看詳情
    """

    @pytest.mark.asyncio
    async def test_query_published_posts_with_pagination(self, client, db_session):
        """
        測試案例：查詢已發布文章列表，支援分頁
        GraphQL 操作：posts query
        預期：返回正確的分頁資料和文章資訊
        """
        # Arrange: 創建 15 篇已發布文章
        for i in range(15):
            await PostFactory.create(
                db_session,
                title=f"Post {i+1}",
                status="published"
            )

        # GraphQL Query
        query = """
            query GetPosts($page: Int!, $limit: Int!) {
                posts(page: $page, limit: $limit, status: PUBLISHED) {
                    edges {
                        node {
                            id
                            title
                            excerpt
                            slug
                            author {
                                username
                                avatarUrl
                            }
                            tags {
                                name
                            }
                            likes
                            commentsCount
                            createdAt
                        }
                    }
                    pageInfo {
                        page
                        pages
                        hasNextPage
                        hasPreviousPage
                        count
                        totalCount
                    }
                }
            }
        """

        # Act: 執行查詢（第一頁，每頁 10 筆）
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "page": 1,
                    "limit": 10
                }
            }
        )

        # Assert: 驗證回應
        assert response.status_code == 200
        data = response.json()

        # 檢查是否有錯誤
        assert "errors" not in data

        # 驗證分頁資訊
        posts_data = data["data"]["posts"]
        assert len(posts_data["edges"]) == 10
        assert posts_data["pageInfo"]["totalCount"] == 15
        assert posts_data["pageInfo"]["hasNextPage"] is True
        assert posts_data["pageInfo"]["hasPreviousPage"] is False
        assert posts_data["pageInfo"]["pages"] == 2

        # 驗證文章資料結構
        first_post = posts_data["edges"][0]["node"]
        assert "id" in first_post
        assert "title" in first_post
        assert "author" in first_post
        assert first_post["title"] == "Post 15"  # 最新的文章應該在前面

    @pytest.mark.asyncio
    async def test_query_single_post_with_nested_data(self, client, db_session):
        """
        測試案例：查詢單一文章，包含所有巢狀資料
        GraphQL 操作：post query
        預期：返回完整的文章資料，包含作者、評論、標籤等
        """
        # Arrange: 創建測試資料
        author = await UserFactory.create(db_session, username="johndoe")
        post = await PostFactory.create(
            db_session,
            author=author,
            title="GraphQL 完整指南",
            slug="graphql-complete-guide"
        )

        # GraphQL Query
        query = """
            query GetPost($slug: String!) {
                post(slug: $slug) {
                    id
                    title
                    content
                    excerpt
                    slug
                    status
                    author {
                        id
                        username
                        bio
                        avatarUrl
                        postsCount
                        followersCount
                    }
                    tags {
                        id
                        name
                        slug
                    }
                    comments {
                        id
                        content
                        author {
                            username
                        }
                        createdAt
                    }
                    likes
                    isLiked
                    readTime
                    createdAt
                    updatedAt
                }
            }
        """

        # Act: 執行查詢
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "slug": "graphql-complete-guide"
                }
            }
        )

        # Assert: 驗證回應
        assert response.status_code == 200
        data = response.json()

        post_data = data["data"]["post"]
        assert post_data["title"] == "GraphQL 完整指南"
        assert post_data["slug"] == "graphql-complete-guide"
        assert post_data["author"]["username"] == "johndoe"
        assert post_data["status"] == "PUBLISHED"
        assert isinstance(post_data["readTime"], int)

    @pytest.mark.asyncio
    async def test_query_posts_with_filters(self, client, db_session):
        """
        測試案例：使用多重過濾條件查詢文章
        GraphQL 操作：posts query with filters
        預期：只返回符合條件的文章
        """
        # Arrange: 創建不同類型的文章
        author1 = await UserFactory.create(db_session)
        author2 = await UserFactory.create(db_session)

        await PostFactory.create(
            db_session,
            author=author1,
            title="Python 教學",
            status="published"
        )
        await PostFactory.create(
            db_session,
            author=author2,
            title="JavaScript 教學",
            status="published"
        )
        await PostFactory.create(
            db_session,
            author=author1,
            title="Python 進階",
            status="draft"
        )

        # GraphQL Query with filters
        query = """
            query FilterPosts($authorId: ID, $status: PostStatus, $search: String) {
                posts(authorId: $authorId, status: $status, search: $search) {
                    edges {
                        node {
                            title
                            status
                            author {
                                id
                            }
                        }
                    }
                    pageInfo {
                        totalCount
                    }
                }
            }
        """

        # Act & Assert: 測試不同的過濾組合

        # 1. 只看特定作者的文章
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "authorId": str(author1.id),
                    "status": "PUBLISHED"
                }
            }
        )
        data = response.json()
        assert data["data"]["posts"]["pageInfo"]["totalCount"] == 1

        # 2. 搜尋關鍵字
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "search": "Python",
                    "status": "PUBLISHED"
                }
            }
        )
        data = response.json()
        assert data["data"]["posts"]["pageInfo"]["totalCount"] == 1
```

---

## GraphQL Mutation 測試範例

### 測試：用戶認證流程

```python
# tests/graphql/mutations/test_auth_mutations.py
import pytest

class TestAuthMutations:
    """
    Feature: 用戶認證功能
    作為新用戶，我想要註冊並登入系統
    """

    @pytest.mark.asyncio
    async def test_register_new_user_successfully(self, client):
        """
        測試案例：成功註冊新用戶
        GraphQL 操作：register mutation
        預期：創建用戶並返回 JWT token
        """
        # GraphQL Mutation
        mutation = """
            mutation Register($input: RegisterInput!) {
                register(input: $input) {
                    user {
                        id
                        email
                        username
                        createdAt
                    }
                    token
                }
            }
        """

        # Act: 執行註冊
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "email": "newuser@example.com",
                        "password": "SecurePass123!",
                        "username": "newuser",
                        "bio": "Hello, I'm new here!"
                    }
                }
            }
        )

        # Assert: 驗證回應
        assert response.status_code == 200
        data = response.json()

        assert "errors" not in data
        register_data = data["data"]["register"]

        # 驗證用戶資料
        assert register_data["user"]["email"] == "newuser@example.com"
        assert register_data["user"]["username"] == "newuser"

        # 驗證 token
        assert len(register_data["token"]) > 0

        # Token 應該是有效的 JWT
        import jwt
        decoded = jwt.decode(
            register_data["token"],
            options={"verify_signature": False}
        )
        assert decoded["sub"] == register_data["user"]["id"]

    @pytest.mark.asyncio
    async def test_register_with_duplicate_email_fails(self, client, db_session):
        """
        測試案例：使用已存在的 email 註冊失敗
        GraphQL 操作：register mutation
        預期：返回錯誤訊息
        """
        # Arrange: 創建已存在的用戶
        await UserFactory.create(
            db_session,
            email="existing@example.com"
        )

        # GraphQL Mutation
        mutation = """
            mutation Register($input: RegisterInput!) {
                register(input: $input) {
                    user {
                        id
                    }
                    token
                }
            }
        """

        # Act: 嘗試用相同 email 註冊
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "email": "existing@example.com",
                        "password": "AnotherPass123!",
                        "username": "anotheruser"
                    }
                }
            }
        )

        # Assert: 驗證錯誤
        assert response.status_code == 200
        data = response.json()

        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "already exists" in data["errors"][0]["message"].lower()

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, client, db_session):
        """
        測試案例：使用正確憑證登入
        GraphQL 操作：login mutation
        預期：返回用戶資料和 token
        """
        # Arrange: 創建測試用戶
        await UserFactory.create(
            db_session,
            email="user@example.com",
            password="TestPass123!"
        )

        # GraphQL Mutation
        mutation = """
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    user {
                        id
                        email
                        username
                    }
                    token
                }
            }
        """

        # Act: 執行登入
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "email": "user@example.com",
                    "password": "TestPass123!"
                }
            }
        )

        # Assert: 驗證成功登入
        assert response.status_code == 200
        data = response.json()

        assert "errors" not in data
        login_data = data["data"]["login"]
        assert login_data["user"]["email"] == "user@example.com"
        assert len(login_data["token"]) > 0
```

### 測試：文章操作

```python
# tests/graphql/mutations/test_post_mutations.py
import pytest

class TestPostMutations:
    """
    Feature: 文章管理功能
    作為作者，我想要創建、編輯和發布文章
    """

    @pytest.mark.asyncio
    async def test_create_post_as_authenticated_user(self, auth_client, db_session):
        """
        測試案例：已認證用戶創建文章
        GraphQL 操作：createPost mutation
        預期：成功創建文章並返回文章資料
        """
        # GraphQL Mutation
        mutation = """
            mutation CreatePost($input: PostInput!) {
                createPost(input: $input) {
                    id
                    title
                    slug
                    content
                    excerpt
                    status
                    author {
                        id
                        username
                    }
                    tags {
                        name
                    }
                    createdAt
                }
            }
        """

        # Act: 創建文章
        response = await auth_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "title": "深入理解 GraphQL",
                        "content": "GraphQL 是一種用於 API 的查詢語言...",
                        "excerpt": "本文將深入探討 GraphQL 的核心概念",
                        "tags": ["GraphQL", "API", "教學"],
                        "status": "DRAFT"
                    }
                }
            }
        )

        # Assert: 驗證文章創建
        assert response.status_code == 200
        data = response.json()

        assert "errors" not in data
        post_data = data["data"]["createPost"]

        assert post_data["title"] == "深入理解 GraphQL"
        assert post_data["slug"] == "shen-ru-li-jie-graphql"  # 自動生成 slug
        assert post_data["status"] == "DRAFT"
        assert post_data["author"]["id"] == str(auth_client.user.id)
        assert len(post_data["tags"]) == 3

    @pytest.mark.asyncio
    async def test_update_own_post_successfully(self, auth_client, db_session):
        """
        測試案例：作者更新自己的文章
        GraphQL 操作：updatePost mutation
        預期：成功更新文章內容
        """
        # Arrange: 創建文章
        post = await PostFactory.create(
            db_session,
            author=auth_client.user,
            title="原始標題",
            status="draft"
        )

        # GraphQL Mutation
        mutation = """
            mutation UpdatePost($id: ID!, $input: PostInput!) {
                updatePost(id: $id, input: $input) {
                    id
                    title
                    content
                    status
                    updatedAt
                }
            }
        """

        # Act: 更新文章
        response = await auth_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "id": str(post.id),
                    "input": {
                        "title": "更新後的標題",
                        "content": "更新後的內容",
                        "status": "PUBLISHED"
                    }
                }
            }
        )

        # Assert: 驗證更新
        assert response.status_code == 200
        data = response.json()

        post_data = data["data"]["updatePost"]
        assert post_data["title"] == "更新後的標題"
        assert post_data["status"] == "PUBLISHED"

    @pytest.mark.asyncio
    async def test_cannot_update_other_users_post(self, auth_client, db_session):
        """
        測試案例：無法更新其他用戶的文章
        GraphQL 操作：updatePost mutation
        預期：返回權限錯誤
        """
        # Arrange: 創建其他用戶的文章
        other_user = await UserFactory.create(db_session)
        post = await PostFactory.create(
            db_session,
            author=other_user,
            title="別人的文章"
        )

        # GraphQL Mutation
        mutation = """
            mutation UpdatePost($id: ID!, $input: PostInput!) {
                updatePost(id: $id, input: $input) {
                    id
                    title
                }
            }
        """

        # Act: 嘗試更新
        response = await auth_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "id": str(post.id),
                    "input": {
                        "title": "嘗試修改"
                    }
                }
            }
        )

        # Assert: 驗證錯誤
        assert response.status_code == 200
        data = response.json()

        assert "errors" in data
        assert "permission" in data["errors"][0]["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_own_post(self, auth_client, db_session):
        """
        測試案例：刪除自己的文章
        GraphQL 操作：deletePost mutation
        預期：成功刪除並返回確認
        """
        # Arrange: 創建文章
        post = await PostFactory.create(
            db_session,
            author=auth_client.user
        )

        # GraphQL Mutation
        mutation = """
            mutation DeletePost($id: ID!) {
                deletePost(id: $id) {
                    success
                    message
                }
            }
        """

        # Act: 刪除文章
        response = await auth_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "id": str(post.id)
                }
            }
        )

        # Assert: 驗證刪除
        assert response.status_code == 200
        data = response.json()

        assert data["data"]["deletePost"]["success"] is True

        # 驗證文章已被刪除
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                }
            }
        """

        response = await auth_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            }
        )

        data = response.json()
        assert data["data"]["post"] is None
```

---

## GraphQL Subscription 測試範例

```python
# tests/graphql/subscriptions/test_subscriptions.py
import pytest
import asyncio
import json
from websockets import connect

class TestSubscriptions:
    """
    Feature: 即時更新功能
    作為用戶，我想要接收即時的評論和文章發布更新
    """

    @pytest.mark.asyncio
    async def test_comment_added_subscription(self, auth_client, db_session):
        """
        測試案例：訂閱新評論更新
        GraphQL 操作：commentAdded subscription
        預期：當新評論加入時收到即時更新
        """
        # Arrange: 創建文章
        post = await PostFactory.create(db_session)

        # GraphQL Subscription
        subscription = """
            subscription OnCommentAdded($postId: ID!) {
                commentAdded(postId: $postId) {
                    id
                    content
                    author {
                        username
                    }
                    createdAt
                }
            }
        """

        # Connect to WebSocket
        async with connect(
            "ws://localhost:8000/graphql",
            subprotocols=["graphql-ws"],
            extra_headers={"Authorization": f"Bearer {auth_client.token}"}
        ) as websocket:

            # Send connection init
            await websocket.send(json.dumps({
                "type": "connection_init",
                "payload": {}
            }))

            # Wait for connection ack
            response = await websocket.recv()
            assert json.loads(response)["type"] == "connection_ack"

            # Subscribe
            await websocket.send(json.dumps({
                "id": "1",
                "type": "start",
                "payload": {
                    "query": subscription,
                    "variables": {"postId": str(post.id)}
                }
            }))

            # Trigger event: Add a comment
            mutation = """
                mutation AddComment($postId: ID!, $content: String!) {
                    createComment(postId: $postId, content: $content) {
                        id
                        content
                    }
                }
            """

            await auth_client.post(
                "/graphql",
                json={
                    "query": mutation,
                    "variables": {
                        "postId": str(post.id),
                        "content": "這是一個測試評論"
                    }
                }
            )

            # Receive subscription update
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            assert data["type"] == "data"
            assert data["payload"]["data"]["commentAdded"]["content"] == "這是一個測試評論"
```

---

## 錯誤處理測試範例

```python
# tests/graphql/test_error_handling.py
import pytest

class TestErrorHandling:
    """
    Feature: 錯誤處理
    系統應該優雅地處理各種錯誤情況
    """

    @pytest.mark.asyncio
    async def test_validation_error_response(self, client):
        """
        測試案例：輸入驗證錯誤
        預期：返回詳細的驗證錯誤訊息
        """
        mutation = """
            mutation Register($input: RegisterInput!) {
                register(input: $input) {
                    user { id }
                    token
                }
            }
        """

        # 提供無效的輸入
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "email": "invalid-email",  # 無效的 email 格式
                        "password": "123",  # 密碼太短
                        "username": "a"  # 用戶名太短
                    }
                }
            }
        )

        data = response.json()
        assert "errors" in data

        # 應該包含多個驗證錯誤
        errors = data["errors"]
        assert any("email" in str(e).lower() for e in errors)
        assert any("password" in str(e).lower() for e in errors)

    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        """
        測試案例：未認證訪問受保護資源
        預期：返回認證錯誤
        """
        mutation = """
            mutation CreatePost($input: PostInput!) {
                createPost(input: $input) {
                    id
                    title
                }
            }
        """

        # 沒有提供認證 token
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "title": "測試文章",
                        "content": "內容"
                    }
                }
            }
        )

        data = response.json()
        assert "errors" in data
        assert "authentication" in data["errors"][0]["message"].lower()
        assert data["errors"][0]["extensions"]["code"] == "UNAUTHENTICATED"

    @pytest.mark.asyncio
    async def test_resource_not_found(self, client):
        """
        測試案例：查詢不存在的資源
        預期：返回 null 而非錯誤
        """
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "id": "00000000-0000-0000-0000-000000000000"
                }
            }
        )

        data = response.json()
        assert "errors" not in data
        assert data["data"]["post"] is None  # GraphQL 慣例：找不到返回 null

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """
        測試案例：超過請求限制
        預期：返回 rate limit 錯誤
        """
        query = """
            query GetPosts {
                posts {
                    edges {
                        node { id }
                    }
                }
            }
        """

        # 快速發送多個請求
        for i in range(101):  # 超過限制 (100/min)
            response = await client.post(
                "/graphql",
                json={"query": query}
            )

        data = response.json()
        assert "errors" in data
        assert "rate limit" in data["errors"][0]["message"].lower()
        assert data["errors"][0]["extensions"]["code"] == "RATE_LIMITED"
```

---

## 服務層測試範例

```python
# tests/services/test_post_service.py
import pytest
from app.services.post_service import PostService
from app.exceptions import PermissionDenied, ValidationError

class TestPostService:
    """
    測試文章服務的業務邏輯
    """

    @pytest.mark.asyncio
    async def test_only_author_can_edit_post(self, db_session):
        """
        測試：只有作者可以編輯文章
        """
        # Arrange
        author = await UserFactory.create(db_session)
        other_user = await UserFactory.create(db_session)
        post = await PostFactory.create(db_session, author=author)

        service = PostService(db_session)

        # Act & Assert: 作者可以編輯
        updated_post = await service.update_post(
            post_id=post.id,
            user_id=author.id,
            data={"title": "更新的標題"}
        )
        assert updated_post.title == "更新的標題"

        # Act & Assert: 其他用戶不能編輯
        with pytest.raises(PermissionDenied) as exc_info:
            await service.update_post(
                post_id=post.id,
                user_id=other_user.id,
                data={"title": "嘗試更新"}
            )
        assert "permission" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_draft_to_published_transition(self, db_session):
        """
        測試：草稿到發布的狀態轉換規則
        """
        # Arrange
        author = await UserFactory.create(db_session)
        post = await PostFactory.create(
            db_session,
            author=author,
            status="draft",
            content="短內容"  # 內容太短
        )

        service = PostService(db_session)

        # Act & Assert: 內容太短無法發布
        with pytest.raises(ValidationError) as exc_info:
            await service.publish_post(post_id=post.id, user_id=author.id)
        assert "content too short" in str(exc_info.value).lower()

        # 更新內容後可以發布
        post.content = "這是一篇完整的文章內容" * 50
        await db_session.commit()

        published_post = await service.publish_post(
            post_id=post.id,
            user_id=author.id
        )
        assert published_post.status == "published"
        assert published_post.published_at is not None

    @pytest.mark.asyncio
    async def test_slug_generation_uniqueness(self, db_session):
        """
        測試：Slug 生成的唯一性
        """
        # Arrange
        author = await UserFactory.create(db_session)
        service = PostService(db_session)

        # 創建第一篇文章
        post1 = await service.create_post(
            user_id=author.id,
            data={
                "title": "GraphQL 教學",
                "content": "內容..."
            }
        )
        assert post1.slug == "graphql-jiao-xue"

        # 創建相同標題的文章，slug 應該不同
        post2 = await service.create_post(
            user_id=author.id,
            data={
                "title": "GraphQL 教學",
                "content": "另一篇內容..."
            }
        )
        assert post2.slug == "graphql-jiao-xue-2"
```

---

## 整合測試範例

```python
# tests/integration/test_user_journey.py
import pytest

class TestUserJourney:
    """
    端到端的用戶旅程測試
    """

    @pytest.mark.asyncio
    async def test_complete_blogging_journey(self, client):
        """
        測試案例：完整的部落格發布流程
        流程：註冊 → 登入 → 創建草稿 → 編輯 → 發布 → 接收評論
        """
        # Step 1: 註冊新用戶
        register_mutation = """
            mutation Register($input: RegisterInput!) {
                register(input: $input) {
                    user { id, username }
                    token
                }
            }
        """

        register_response = await client.post(
            "/graphql",
            json={
                "query": register_mutation,
                "variables": {
                    "input": {
                        "email": "blogger@example.com",
                        "password": "SecurePass123!",
                        "username": "blogger"
                    }
                }
            }
        )

        register_data = register_response.json()["data"]["register"]
        user_id = register_data["user"]["id"]
        token = register_data["token"]

        # 設置認證
        client.headers["Authorization"] = f"Bearer {token}"

        # Step 2: 創建草稿
        create_draft_mutation = """
            mutation CreateDraft($input: PostInput!) {
                createPost(input: $input) {
                    id
                    title
                    status
                }
            }
        """

        draft_response = await client.post(
            "/graphql",
            json={
                "query": create_draft_mutation,
                "variables": {
                    "input": {
                        "title": "我的第一篇文章",
                        "content": "初始內容",
                        "status": "DRAFT"
                    }
                }
            }
        )

        draft_data = draft_response.json()["data"]["createPost"]
        post_id = draft_data["id"]
        assert draft_data["status"] == "DRAFT"

        # Step 3: 編輯草稿
        update_mutation = """
            mutation UpdatePost($id: ID!, $input: PostInput!) {
                updatePost(id: $id, input: $input) {
                    id
                    title
                    content
                }
            }
        """

        await client.post(
            "/graphql",
            json={
                "query": update_mutation,
                "variables": {
                    "id": post_id,
                    "input": {
                        "title": "我的第一篇完整文章",
                        "content": "這是一篇關於 GraphQL 的深入探討..." * 20
                    }
                }
            }
        )

        # Step 4: 發布文章
        publish_mutation = """
            mutation PublishPost($id: ID!) {
                publishPost(id: $id) {
                    id
                    status
                    publishedAt
                }
            }
        """

        publish_response = await client.post(
            "/graphql",
            json={
                "query": publish_mutation,
                "variables": {"id": post_id}
            }
        )

        publish_data = publish_response.json()["data"]["publishPost"]
        assert publish_data["status"] == "PUBLISHED"
        assert publish_data["publishedAt"] is not None

        # Step 5: 其他用戶評論
        # 創建另一個用戶
        reader_response = await client.post(
            "/graphql",
            json={
                "query": register_mutation,
                "variables": {
                    "input": {
                        "email": "reader@example.com",
                        "password": "ReaderPass123!",
                        "username": "reader"
                    }
                }
            }
        )

        reader_token = reader_response.json()["data"]["register"]["token"]
        client.headers["Authorization"] = f"Bearer {reader_token}"

        # 添加評論
        comment_mutation = """
            mutation AddComment($postId: ID!, $content: String!) {
                createComment(postId: $postId, content: $content) {
                    id
                    content
                    author { username }
                }
            }
        """

        comment_response = await client.post(
            "/graphql",
            json={
                "query": comment_mutation,
                "variables": {
                    "postId": post_id,
                    "content": "很棒的文章！學到很多。"
                }
            }
        )

        comment_data = comment_response.json()["data"]["createComment"]
        assert comment_data["author"]["username"] == "reader"

        # Step 6: 驗證完整的文章資料
        final_query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    title
                    status
                    author { username }
                    comments {
                        content
                        author { username }
                    }
                    likes
                }
            }
        """

        final_response = await client.post(
            "/graphql",
            json={
                "query": final_query,
                "variables": {"id": post_id}
            }
        )

        final_data = final_response.json()["data"]["post"]
        assert final_data["author"]["username"] == "blogger"
        assert len(final_data["comments"]) == 1
        assert final_data["comments"][0]["author"]["username"] == "reader"

    @pytest.mark.asyncio
    async def test_search_and_discovery_flow(self, client, db_session):
        """
        測試案例：搜尋與發現流程
        流程：創建多篇文章 → 搜尋 → 過濾 → 查看相關文章
        """
        # Arrange: 創建測試資料
        author = await UserFactory.create(db_session)

        # 創建不同主題的文章
        posts = []
        topics = [
            ("GraphQL 基礎教學", "GraphQL 是一種查詢語言", ["GraphQL", "API"]),
            ("REST vs GraphQL", "比較兩種 API 設計", ["GraphQL", "REST", "API"]),
            ("Python 異步編程", "深入了解 asyncio", ["Python", "Async"]),
            ("FastAPI 完整指南", "使用 FastAPI 建立 API", ["Python", "FastAPI", "API"])
        ]

        for title, content, tags in topics:
            post = await PostFactory.create(
                db_session,
                author=author,
                title=title,
                content=content * 50,
                status="published"
            )
            posts.append(post)

        # Step 1: 全文搜尋
        search_query = """
            query Search($query: String!) {
                search(query: $query) {
                    ... on Post {
                        id
                        title
                        excerpt
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": search_query,
                "variables": {"query": "GraphQL"}
            }
        )

        search_results = response.json()["data"]["search"]
        assert len(search_results) == 2  # 應該找到兩篇 GraphQL 相關文章

        # Step 2: 標籤過濾
        tag_filter_query = """
            query PostsByTag($tag: String!) {
                posts(tag: $tag) {
                    edges {
                        node {
                            title
                            tags { name }
                        }
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": tag_filter_query,
                "variables": {"tag": "API"}
            }
        )

        tagged_posts = response.json()["data"]["posts"]["edges"]
        assert len(tagged_posts) == 3  # 三篇文章有 API 標籤

        # Step 3: 查看相關文章（需要 pgvector）
        # 這部分在實際實作 pgvector 後測試
```

---

## 測試執行與報告

### 執行測試

```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/graphql/queries/test_post_queries.py

# 執行特定測試類別
pytest tests/graphql/mutations/test_auth_mutations.py::TestAuthMutations

# 執行特定測試方法
pytest tests/graphql/mutations/test_auth_mutations.py::TestAuthMutations::test_register_new_user_successfully

# 顯示詳細輸出
pytest -v

# 顯示 print 輸出
pytest -s

# 執行並顯示覆蓋率
pytest --cov=app --cov-report=html

# 只執行標記的測試
pytest -m "graphql"

# 平行執行測試
pytest -n auto
```

### 測試標記使用

```python
@pytest.mark.asyncio  # 異步測試
@pytest.mark.graphql  # GraphQL 測試
@pytest.mark.slow     # 慢速測試
@pytest.mark.unit     # 單元測試
@pytest.mark.integration  # 整合測試
```

---

這些測試範例展示了 GraphQL-First TDD 的實踐方式，每個測試都是完整的 GraphQL 操作範例，可以直接作為 API 文件使用。