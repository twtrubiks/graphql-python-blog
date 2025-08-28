import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.auth import AuthService


class TestMeQuery:
    """測試 me query (取得當前用戶)"""

    @pytest.mark.asyncio
    async def test_me_query_with_valid_token(self, client: AsyncClient, test_session: AsyncSession):
        """測試使用有效 token 查詢當前用戶"""
        # 創建測試用戶
        user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=AuthService.get_password_hash("Password123!")
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # 生成 token
        token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        query = """
            query Me {
                me {
                    id
                    email
                    username
                    isActive
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 檢查回應
        assert "data" in data
        assert "me" in data["data"]
        me_data = data["data"]["me"]
        assert me_data["id"] == user.id  # id should be integer
        assert me_data["email"] == "testuser@example.com"
        assert me_data["username"] == "testuser"
        assert me_data["isActive"] is True

    @pytest.mark.asyncio
    async def test_me_query_without_token(self, client: AsyncClient):
        """測試無 token 時查詢當前用戶"""
        query = """
            query Me {
                me {
                    id
                    email
                    username
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回 null
        assert "data" in data
        assert data["data"]["me"] is None

    @pytest.mark.asyncio
    async def test_me_query_with_invalid_token(self, client: AsyncClient):
        """測試使用無效 token 查詢當前用戶"""
        query = """
            query Me {
                me {
                    id
                    email
                    username
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回 null
        assert "data" in data
        assert data["data"]["me"] is None

    @pytest.mark.asyncio
    async def test_me_query_with_expired_token(self, client: AsyncClient, test_session: AsyncSession):
        """測試使用過期 token 查詢當前用戶"""

        # 創建測試用戶
        user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=AuthService.get_password_hash("Password123!")
        )
        test_session.add(user)
        await test_session.commit()

        # 生成過期的 token
        token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(seconds=-1)  # 已經過期
        )

        query = """
            query Me {
                me {
                    id
                    email
                    username
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回 null
        assert "data" in data
        assert data["data"]["me"] is None

    @pytest.mark.asyncio
    async def test_me_query_with_inactive_user(self, client: AsyncClient, test_session: AsyncSession):
        """測試停用用戶的 token 查詢"""
        # 創建停用的用戶
        user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password=AuthService.get_password_hash("Password123!"),
            is_active=False
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # 生成 token
        token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        query = """
            query Me {
                me {
                    id
                    email
                    username
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 停用的用戶應該返回 null
        assert "data" in data
        assert data["data"]["me"] is None


class TestUserQuery:
    """測試 user query (查詢單一用戶)"""

    @pytest.mark.asyncio
    async def test_user_query_by_id(self, client: AsyncClient, test_session: AsyncSession):
        """測試根據 ID 查詢單一用戶"""
        # 創建測試用戶
        user = User(
            email="queryuser@example.com",
            username="queryuser",
            hashed_password=AuthService.get_password_hash("Password123!"),
            bio="Test user bio",
            avatar_url="https://example.com/avatar.jpg"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        query = """
            query GetUser($userId: Int!) {
                user(id: $userId) {
                    id
                    email
                    username
                    bio
                    avatarUrl
                    isActive
                    createdAt
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

        assert response.status_code == 200
        data = response.json()

        # 檢查回應
        assert "data" in data
        assert "user" in data["data"]
        user_data = data["data"]["user"]
        assert user_data["id"] == user.id
        assert user_data["email"] == "queryuser@example.com"
        assert user_data["username"] == "queryuser"
        assert user_data["bio"] == "Test user bio"
        assert user_data["avatarUrl"] == "https://example.com/avatar.jpg"
        assert user_data["isActive"] is True

    @pytest.mark.asyncio
    async def test_user_query_by_username(self, client: AsyncClient, test_session: AsyncSession):
        """測試根據 username 查詢單一用戶"""
        # 創建測試用戶
        user = User(
            email="testusername@example.com",
            username="uniqueusername",
            hashed_password=AuthService.get_password_hash("Password123!")
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        query = """
            query GetUserByUsername($username: String!) {
                user(username: $username) {
                    id
                    email
                    username
                    isActive
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"username": "uniqueusername"}
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 檢查回應
        assert "data" in data
        assert "user" in data["data"]
        user_data = data["data"]["user"]
        assert user_data["id"] == user.id
        assert user_data["email"] == "testusername@example.com"
        assert user_data["username"] == "uniqueusername"
        assert user_data["isActive"] is True

    @pytest.mark.asyncio
    async def test_user_query_nonexistent_user(self, client: AsyncClient):
        """測試查詢不存在的用戶"""
        query = """
            query GetUser($userId: Int!) {
                user(id: $userId) {
                    id
                    email
                    username
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"userId": 99999}
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回 null 或錯誤
        assert "data" in data
        assert data["data"]["user"] is None

    @pytest.mark.asyncio
    async def test_user_query_inactive_user(self, client: AsyncClient, test_session: AsyncSession):
        """測試查詢停用的用戶"""
        # 創建停用的用戶
        user = User(
            email="inactivequery@example.com",
            username="inactivequeryuser",
            hashed_password=AuthService.get_password_hash("Password123!"),
            is_active=False
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        query = """
            query GetUser($userId: Int!) {
                user(id: $userId) {
                    id
                    email
                    username
                    isActive
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

        assert response.status_code == 200
        data = response.json()

        # 停用的用戶仍應該可以查詢到，但 isActive 應該是 False
        assert "data" in data
        assert "user" in data["data"]
        user_data = data["data"]["user"]
        assert user_data["id"] == user.id
        assert user_data["isActive"] is False

    @pytest.mark.asyncio
    async def test_user_query_without_sensitive_data(self, client: AsyncClient, test_session: AsyncSession):
        """測試查詢用戶時不應返回敏感資料（如密碼）"""
        # 創建測試用戶
        user = User(
            email="secure@example.com",
            username="secureuser",
            hashed_password=AuthService.get_password_hash("Password123!")
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        query = """
            query GetUser($userId: Int!) {
                user(id: $userId) {
                    id
                    email
                    username
                    bio
                    avatarUrl
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

        assert response.status_code == 200
        data = response.json()

        # 檢查回應
        assert "data" in data
        assert "user" in data["data"]
        user_data = data["data"]["user"]

        # 確保沒有密碼相關的欄位
        assert "password" not in user_data
        assert "hashedPassword" not in user_data
        assert "hashed_password" not in user_data


class TestUsersQuery:
    """測試 users query (用戶列表)"""

    @pytest.mark.asyncio
    async def test_users_query_basic(self, client: AsyncClient, test_session: AsyncSession):
        """測試基本的用戶列表查詢"""
        # 創建測試用戶
        users = []
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                hashed_password=AuthService.get_password_hash("Password123!")
            )
            users.append(user)
            test_session.add(user)

        await test_session.commit()

        query = """
            query GetUsers {
                users {
                    id
                    email
                    username
                    isActive
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "users" in data["data"]
        assert len(data["data"]["users"]) == 5

        # 驗證返回的用戶資料
        for i, user_data in enumerate(data["data"]["users"]):
            assert "id" in user_data
            assert "email" in user_data
            assert "username" in user_data
            assert user_data["isActive"] is True

    @pytest.mark.asyncio
    async def test_users_query_with_pagination(self, client: AsyncClient, test_session: AsyncSession):
        """測試用戶列表分頁查詢"""
        # 創建 15 個測試用戶
        for i in range(15):
            user = User(
                email=f"page_user{i}@example.com",
                username=f"page_user{i}",
                hashed_password=AuthService.get_password_hash("Password123!")
            )
            test_session.add(user)

        await test_session.commit()

        query = """
            query GetUsersPage($page: Int!, $limit: Int!) {
                users(page: $page, limit: $limit) {
                    id
                    username
                }
            }
        """

        # 查詢第一頁
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"page": 1, "limit": 10}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "users" in data["data"]
        assert len(data["data"]["users"]) == 10

        # 查詢第二頁
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"page": 2, "limit": 10}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["users"]) == 5  # 剩餘 5 個用戶

    @pytest.mark.asyncio
    async def test_users_query_empty_list(self, client: AsyncClient):
        """測試空的用戶列表"""
        query = """
            query GetUsers {
                users {
                    id
                    username
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "users" in data["data"]
        assert data["data"]["users"] == []

    @pytest.mark.asyncio
    async def test_users_query_filter_active(self, client: AsyncClient, test_session: AsyncSession):
        """測試過濾活躍用戶"""
        # 創建活躍和非活躍用戶
        active_user = User(
            email="active@example.com",
            username="activeuser",
            hashed_password=AuthService.get_password_hash("Password123!"),
            is_active=True
        )
        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password=AuthService.get_password_hash("Password123!"),
            is_active=False
        )

        test_session.add(active_user)
        test_session.add(inactive_user)
        await test_session.commit()

        query = """
            query GetActiveUsers($isActive: Boolean) {
                users(isActive: $isActive) {
                    id
                    username
                    isActive
                }
            }
        """

        # 查詢活躍用戶
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"isActive": True}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["users"]) == 1
        assert data["data"]["users"][0]["username"] == "activeuser"
        assert data["data"]["users"][0]["isActive"] is True

        # 查詢非活躍用戶
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"isActive": False}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["users"]) == 1
        assert data["data"]["users"][0]["username"] == "inactiveuser"
        assert data["data"]["users"][0]["isActive"] is False

    @pytest.mark.asyncio
    async def test_users_query_ordering(self, client: AsyncClient, test_session: AsyncSession):
        """測試用戶列表排序"""

        # 創建不同時間的用戶
        for i in range(3):
            user = User(
                email=f"order_user{i}@example.com",
                username=f"order_user{i}",
                hashed_password=AuthService.get_password_hash("Password123!")
            )
            # 手動設置創建時間（測試環境允許）
            user.created_at = datetime.now(timezone.utc) - timedelta(days=i)
            test_session.add(user)

        await test_session.commit()

        query = """
            query GetUsersOrdered {
                users {
                    id
                    username
                    createdAt
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        users = data["data"]["users"]
        assert len(users) == 3

        # 驗證預設按創建時間降序排列（最新的在前）
        assert "order_user0" in users[0]["username"]
        assert "order_user2" in users[-1]["username"]


class TestAuthenticatedQueries:
    """測試需要認證的查詢"""

    @pytest.mark.asyncio
    async def test_protected_query_with_auth(self, client: AsyncClient, test_session: AsyncSession):
        """測試認證後可以訪問受保護的查詢"""
        # 創建測試用戶
        user = User(
            email="authuser@example.com",
            username="authuser",
            hashed_password=AuthService.get_password_hash("Password123!")
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # 生成 token
        token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        query = """
            query ProtectedData {
                protectedData {
                    message
                    userId
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該成功獲取資料
        assert "data" in data
        assert "protectedData" in data["data"]
        protected = data["data"]["protectedData"]
        assert protected["message"] == "This is protected data"
        assert protected["userId"] == str(user.id)  # userId should be string in this case

    @pytest.mark.asyncio
    async def test_protected_query_without_auth(self, client: AsyncClient):
        """測試未認證時無法訪問受保護的查詢"""
        query = """
            query ProtectedData {
                protectedData {
                    message
                    userId
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "authentication required" in data["errors"][0]["message"].lower()