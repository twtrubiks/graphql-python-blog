import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.auth import AuthService


class TestRegisterMutation:
    """測試註冊 mutation"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_session: AsyncSession):
        """測試成功註冊新用戶"""
        mutation = """
            mutation Register($email: String!, $password: String!, $username: String!) {
                register(email: $email, password: $password, username: $username) {
                    user {
                        id
                        email
                        username
                    }
                    token
                }
            }
        """
        
        variables = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "username": "newuser"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 檢查回應結構
        assert "data" in data
        assert "register" in data["data"]
        assert "user" in data["data"]["register"]
        assert "token" in data["data"]["register"]
        
        # 檢查用戶資料
        user_data = data["data"]["register"]["user"]
        assert user_data["email"] == "newuser@example.com"
        assert user_data["username"] == "newuser"
        assert "id" in user_data
        
        # 檢查 token
        token = data["data"]["register"]["token"]
        assert token is not None
        assert len(token) > 0
        
        # 驗證用戶已存在資料庫中
        from sqlalchemy import select
        result = await test_session.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.username == "newuser"
        
        # 驗證密碼已加密
        assert user.hashed_password != "SecurePass123!"
        assert AuthService.verify_password("SecurePass123!", user.hashed_password)
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_session: AsyncSession):
        """測試重複 email 註冊失敗"""
        # 先創建一個用戶
        existing_user = User(
            email="existing@example.com",
            username="existinguser",
            hashed_password=AuthService.get_password_hash("password123")
        )
        test_session.add(existing_user)
        await test_session.commit()
        
        mutation = """
            mutation Register($email: String!, $password: String!, $username: String!) {
                register(email: $email, password: $password, username: $username) {
                    user {
                        id
                        email
                        username
                    }
                    token
                }
            }
        """
        
        variables = {
            "email": "existing@example.com",  # 重複的 email
            "password": "NewPassword123!",
            "username": "newusername"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "already registered" in data["errors"][0]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_session: AsyncSession):
        """測試重複 username 註冊失敗"""
        # 先創建一個用戶
        existing_user = User(
            email="user1@example.com",
            username="existinguser",
            hashed_password=AuthService.get_password_hash("password123")
        )
        test_session.add(existing_user)
        await test_session.commit()
        
        mutation = """
            mutation Register($email: String!, $password: String!, $username: String!) {
                register(email: $email, password: $password, username: $username) {
                    user {
                        id
                        email
                        username
                    }
                    token
                }
            }
        """
        
        variables = {
            "email": "newuser@example.com",
            "password": "NewPassword123!",
            "username": "existinguser"  # 重複的 username
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "already taken" in data["errors"][0]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """測試無效 email 格式"""
        mutation = """
            mutation Register($email: String!, $password: String!, $username: String!) {
                register(email: $email, password: $password, username: $username) {
                    user {
                        id
                        email
                        username
                    }
                    token
                }
            }
        """
        
        variables = {
            "email": "invalid-email",  # 無效的 email 格式
            "password": "SecurePass123!",
            "username": "validuser"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "invalid email" in data["errors"][0]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """測試弱密碼"""
        mutation = """
            mutation Register($email: String!, $password: String!, $username: String!) {
                register(email: $email, password: $password, username: $username) {
                    user {
                        id
                        email
                        username
                    }
                    token
                }
            }
        """
        
        variables = {
            "email": "user@example.com",
            "password": "123",  # 太弱的密碼
            "username": "validuser"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "password" in data["errors"][0]["message"].lower()


class TestLoginMutation:
    """測試登入 mutation"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_session: AsyncSession):
        """測試成功登入"""
        # 先創建一個用戶
        password = "SecurePass123!"
        hashed_password = AuthService.get_password_hash(password)
        user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=hashed_password
        )
        test_session.add(user)
        await test_session.commit()
        
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
        
        variables = {
            "email": "testuser@example.com",
            "password": password
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 檢查回應結構
        assert "data" in data
        assert "login" in data["data"]
        assert "user" in data["data"]["login"]
        assert "token" in data["data"]["login"]
        
        # 檢查用戶資料
        user_data = data["data"]["login"]["user"]
        assert user_data["email"] == "testuser@example.com"
        assert user_data["username"] == "testuser"
        assert "id" in user_data
        
        # 檢查 token
        token = data["data"]["login"]["token"]
        assert token is not None
        assert len(token) > 0
        
        # 驗證 token 是有效的 JWT
        payload = AuthService.verify_token(token)
        assert payload is not None
        assert payload["sub"] == str(user.id)
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_session: AsyncSession):
        """測試錯誤密碼登入失敗"""
        # 先創建一個用戶
        user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=AuthService.get_password_hash("CorrectPassword123!")
        )
        test_session.add(user)
        await test_session.commit()
        
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
        
        variables = {
            "email": "testuser@example.com",
            "password": "WrongPassword123!"  # 錯誤的密碼
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        error_message = data["errors"][0]["message"].lower()
        assert "invalid" in error_message or "incorrect" in error_message
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient, test_session: AsyncSession):
        """測試不存在的用戶登入失敗"""
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
        
        variables = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤
        assert "errors" in data
        assert len(data["errors"]) > 0
        error_message = data["errors"][0]["message"].lower()
        assert "invalid" in error_message or "not found" in error_message
    
    @pytest.mark.asyncio
    async def test_login_with_username_instead_of_email(self, client: AsyncClient, test_session: AsyncSession):
        """測試使用 username 而非 email 登入（應該失敗）"""
        # 先創建一個用戶
        user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=AuthService.get_password_hash("Password123!")
        )
        test_session.add(user)
        await test_session.commit()
        
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
        
        variables = {
            "email": "testuser",  # 使用 username 而非 email
            "password": "Password123!"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 應該有錯誤或沒有找到用戶
        assert "errors" in data or data["data"]["login"] is None