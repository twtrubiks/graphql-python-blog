import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.graphql.subscriptions.comment import CommentEvent
from app.graphql.subscriptions.user_status import UserStatusEvent, UserStatus
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment as CommentModel
from app.graphql.types.comment import Comment as CommentType
from app.graphql.utils import convert_model_to_graphql
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestSubscriptionIntegration:
    """測試 Subscription 整合功能"""
    
    async def test_graphql_schema_includes_subscriptions(self):
        """測試 GraphQL Schema 包含 Subscription 類型"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            query = """
                query {
                    __schema {
                        subscriptionType {
                            name
                            fields {
                                name
                                description
                            }
                        }
                    }
                }
            """
            
            response = await client.post(
                "/graphql",
                json={"query": query}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 檢查 Subscription 類型存在
            subscription_type = data["data"]["__schema"]["subscriptionType"]
            assert subscription_type is not None
            assert subscription_type["name"] == "Subscription"
            
            # 檢查包含預期的 subscription fields
            field_names = [field["name"] for field in subscription_type["fields"]]
            assert "commentAdded" in field_names
            assert "userStatusChanged" in field_names
    
    async def test_comment_subscription_query_format(self):
        """測試評論訂閱查詢格式"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 驗證 subscription 查詢格式
            query = """
                query IntrospectionQuery {
                    __type(name: "Subscription") {
                        fields {
                            name
                            args {
                                name
                                type {
                                    name
                                    kind
                                }
                            }
                        }
                    }
                }
            """
            
            response = await client.post(
                "/graphql",
                json={"query": query}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 找到 commentAdded field
            fields = data["data"]["__type"]["fields"]
            comment_added = next((f for f in fields if f["name"] == "commentAdded"), None)
            
            assert comment_added is not None
            # 檢查參數
            args = comment_added["args"]
            assert len(args) > 0
            assert any(arg["name"] == "postId" for arg in args)
    
    async def test_user_status_subscription_query_format(self):
        """測試用戶狀態訂閱查詢格式"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            query = """
                query IntrospectionQuery {
                    __type(name: "Subscription") {
                        fields {
                            name
                            type {
                                name
                                kind
                            }
                        }
                    }
                }
            """
            
            response = await client.post(
                "/graphql",
                json={"query": query}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 找到 userStatusChanged field
            fields = data["data"]["__type"]["fields"]
            user_status = next((f for f in fields if f["name"] == "userStatusChanged"), None)
            
            assert user_status is not None
    
    async def test_comment_event_manager_integration(self, test_session):
        """測試評論事件管理器整合"""
        # 創建測試用戶
        user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=get_password_hash("password123")
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        post = Post(
            title="Test Post",
            content="Test content",
            author_id=user.id,
            slug="test-post"
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)
        
        # 訂閱評論事件
        post_id_str = str(post.id)
        queue = CommentEvent.subscribe(post_id_str)
        
        # 創建評論
        comment = CommentModel(
            content="Test comment",
            post_id=post.id,
            user_id=user.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)
        
        # 發布評論事件
        comment_type = convert_model_to_graphql(comment, CommentType)
        await CommentEvent.publish(post_id_str, comment_type)
        
        # 驗證收到事件
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.id == str(comment.id)
        assert received.content == comment.content
        
        # 清理
        CommentEvent.unsubscribe(post_id_str, queue)
    
    async def test_user_status_event_manager_integration(self):
        """測試用戶狀態事件管理器整合"""
        # 訂閱狀態事件
        queue = UserStatusEvent.subscribe()
        
        # 模擬用戶上線
        await UserStatusEvent.publish_status_change(
            user_id="test_user",
            username="testuser",
            status=UserStatus.ONLINE
        )
        
        # 驗證收到事件
        status_change = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert status_change.user_id == "test_user"
        assert status_change.username == "testuser"
        assert status_change.status == UserStatus.ONLINE
        
        # 清理
        UserStatusEvent.unsubscribe(queue)
    
    async def test_websocket_endpoint_available(self):
        """測試 WebSocket 端點可用"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # GraphQL endpoint 應該支援 WebSocket 升級
            response = await client.get("/graphql")
            # 端點應該存在（即使 GET 可能不被允許）
            assert response.status_code in [200, 405, 400]