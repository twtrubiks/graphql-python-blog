import pytest
from httpx import AsyncClient
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
        from datetime import timedelta
        
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