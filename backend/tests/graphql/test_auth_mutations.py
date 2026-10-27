import pytest
from httpx import AsyncClient
from sqlalchemy import select
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
                        isActive
                        isSuperuser
                        createdAt
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
        # email 因為權限保護可能是 None
        # assert user_data["email"] == "newuser@example.com"
        assert user_data["username"] == "newuser"
        assert "id" in user_data
        # 新帳號是啟用狀態，而且不能是管理員（is_superuser 的預設值）
        assert user_data["isActive"] is True
        assert user_data["isSuperuser"] is False
        assert user_data["createdAt"] is not None

        # 檢查 token
        token = data["data"]["register"]["token"]
        assert token is not None
        assert len(token) > 0

        # 驗證用戶已存在資料庫中
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
        assert data["errors"][0]["message"] == "Email already registered"

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
        assert data["errors"][0]["message"] == "Username already taken"

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
        assert data["errors"][0]["message"] == "Invalid email format"

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
        assert data["errors"][0]["message"] == "Password must be at least 8 characters long"

    REGISTER_MUTATION = """
        mutation Register($email: String!, $password: String!, $username: String!) {
            register(email: $email, password: $password, username: $username) { user { username } }
        }
    """

    async def register_with_password(self, client: AsyncClient, password: str) -> dict:
        response = await client.post(
            "/graphql",
            json={
                "query": self.REGISTER_MUTATION,
                "variables": {"email": "user@example.com", "password": password, "username": "validuser"}
            }
        )
        return response.json()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("password, expected_error", [
        ("Abcdef1", "Password must be at least 8 characters long"),  # 7 字元
        ("abcdefg1", "Password must contain at least one uppercase letter"),
        ("ABCDEFG1", "Password must contain at least one lowercase letter"),
        ("Abcdefgh", "Password must contain at least one number"),
    ], ids=["7-chars", "no-upper", "no-lower", "no-number"])
    async def test_register_password_rules(self, client: AsyncClient, password, expected_error):
        data = await self.register_with_password(client, password)

        assert data["errors"][0]["message"] == expected_error

    @pytest.mark.asyncio
    async def test_register_password_exactly_8_chars(self, client: AsyncClient):
        """長度下限是 8，剛好 8 個字元要能註冊"""
        data = await self.register_with_password(client, "Abcdefg1")

        assert "errors" not in data, data["errors"]
        assert data["data"]["register"]["user"]["username"] == "validuser"


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
        # email 因為權限保護可能是 None
        # assert user_data["email"] == "testuser@example.com"
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
        # token 存在瀏覽器裡、任何人都能解碼，只放必要的 sub 與 exp，不放 email 等個資
        assert set(payload) == {"sub", "exp"}

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
        assert data["errors"][0]["message"] == "Invalid email or password"

    @pytest.mark.asyncio
    async def test_login_disabled_account(self, client: AsyncClient, test_session: AsyncSession):
        """停用的帳號密碼正確也不能登入，不會拿到 token"""
        user = User(
            email="disabled@example.com",
            username="disableduser",
            hashed_password=AuthService.get_password_hash("CorrectPassword123!"),
            is_active=False
        )
        test_session.add(user)
        await test_session.commit()

        mutation = """
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    token
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {
                "email": "disabled@example.com", "password": "CorrectPassword123!"
            }}
        )

        data = response.json()
        assert data["data"] is None
        assert data["errors"][0]["message"] == "User account is disabled"

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
        # 與密碼錯誤相同的訊息，避免洩漏 email 是否已註冊
        assert data["errors"][0]["message"] == "Invalid email or password"

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

        # 找不到用戶，應回傳與密碼錯誤相同的訊息（避免洩漏帳號是否存在）
        assert data["data"] is None
        assert data["errors"][0]["message"] == "Invalid email or password"