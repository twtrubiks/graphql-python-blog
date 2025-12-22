import pytest
import asyncio
from datetime import datetime
from app.graphql.subscriptions.user_status import (
    UserStatusEvent,
    UserStatusSubscription,
    UserStatus,
    OnlineUserInfo,
)
from app.graphql.queries.user import get_online_users


@pytest.mark.asyncio
class TestUserStatusSubscription:
    """測試用戶狀態變更通知功能"""
    
    async def test_user_online_status_notification(self):
        """測試用戶上線狀態變更通知"""
        user_id = "user1"
        username = "testuser"
        
        # 訂閱狀態變更
        queue = UserStatusEvent.subscribe()
        
        # 發布上線狀態
        await UserStatusEvent.publish_status_change(
            user_id=user_id,
            username=username,
            status=UserStatus.ONLINE
        )
        
        # 檢查是否收到通知
        status_change = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert status_change.user_id == user_id
        assert status_change.username == username
        assert status_change.status == UserStatus.ONLINE
        assert isinstance(status_change.timestamp, datetime)
        
        # 驗證狀態已更新
        assert UserStatusEvent.get_user_status(user_id) == UserStatus.ONLINE
        
        # 清理
        UserStatusEvent.unsubscribe(queue)
    
    async def test_user_offline_status_notification(self):
        """測試用戶離線狀態變更通知"""
        user_id = "user2"
        username = "testuser2"
        
        # 訂閱狀態變更
        queue = UserStatusEvent.subscribe()
        
        # 先設置為上線
        await UserStatusEvent.publish_status_change(
            user_id=user_id,
            username=username,
            status=UserStatus.ONLINE
        )
        
        # 清空 queue
        await asyncio.wait_for(queue.get(), timeout=1.0)
        
        # 發布離線狀態
        await UserStatusEvent.publish_status_change(
            user_id=user_id,
            username=username,
            status=UserStatus.OFFLINE
        )
        
        # 檢查是否收到離線通知
        status_change = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert status_change.user_id == user_id
        assert status_change.username == username
        assert status_change.status == UserStatus.OFFLINE
        
        # 驗證狀態已更新
        assert UserStatusEvent.get_user_status(user_id) == UserStatus.OFFLINE
        
        # 清理
        UserStatusEvent.unsubscribe(queue)
    
    async def test_status_sync_accuracy(self):
        """測試狀態同步準確性"""
        users = [
            ("user1", "alice", UserStatus.ONLINE),
            ("user2", "bob", UserStatus.OFFLINE),
            ("user3", "charlie", UserStatus.ONLINE),
        ]
        
        # 訂閱狀態變更
        queue = UserStatusEvent.subscribe()
        
        # 發布多個用戶狀態
        for user_id, username, status in users:
            await UserStatusEvent.publish_status_change(
                user_id=user_id,
                username=username,
                status=status
            )
        
        # 驗證每個狀態都被正確記錄
        for user_id, _, expected_status in users:
            actual_status = UserStatusEvent.get_user_status(user_id)
            assert actual_status == expected_status
        
        # 驗證收到了所有狀態變更通知
        received_changes = []
        for _ in users:
            change = await asyncio.wait_for(queue.get(), timeout=1.0)
            received_changes.append(change)
        
        assert len(received_changes) == len(users)
        
        # 清理
        UserStatusEvent.unsubscribe(queue)
    
    async def test_multiple_subscribers(self):
        """測試多個訂閱者同時接收狀態變更"""
        user_id = "user1"
        username = "testuser"
        
        # 多個訂閱者
        queue1 = UserStatusEvent.subscribe()
        queue2 = UserStatusEvent.subscribe()
        queue3 = UserStatusEvent.subscribe()
        
        # 發布狀態變更
        await UserStatusEvent.publish_status_change(
            user_id=user_id,
            username=username,
            status=UserStatus.ONLINE
        )
        
        # 所有訂閱者都應該收到通知
        change1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        change2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
        change3 = await asyncio.wait_for(queue3.get(), timeout=1.0)
        
        assert change1.user_id == user_id
        assert change2.user_id == user_id
        assert change3.user_id == user_id
        
        # 清理
        UserStatusEvent.unsubscribe(queue1)
        UserStatusEvent.unsubscribe(queue2)
        UserStatusEvent.unsubscribe(queue3)
    
    async def test_user_status_subscription_resolver(self):
        """測試 GraphQL subscription resolver"""
        subscription = UserStatusSubscription()

        # 開始訂閱（使用參數傳入 user_id 和 username）
        subscription_gen = subscription.user_status_changed(
            user_id="subscriber1",
            username="subscriber_user"
        )

        # 在另一個協程中發布狀態變更（由另一個用戶）
        async def publish_status_changes():
            await asyncio.sleep(0.1)
            await UserStatusEvent.publish_status_change(
                user_id="user1",
                username="alice",
                status=UserStatus.ONLINE
            )

        # 啟動發布任務
        publish_task = asyncio.create_task(publish_status_changes())

        # 第一個事件是訂閱者自己的 ONLINE 狀態
        status_change = await anext(subscription_gen)
        assert status_change.user_id == "subscriber1"
        assert status_change.username == "subscriber_user"
        assert status_change.status == UserStatus.ONLINE

        # 第二個事件是其他用戶的狀態變更
        status_change = await anext(subscription_gen)
        assert status_change.user_id == "user1"
        assert status_change.username == "alice"
        assert status_change.status == UserStatus.ONLINE

        # 清理
        await publish_task
        await subscription_gen.aclose()
    
    async def test_default_offline_status(self):
        """測試預設離線狀態"""
        # 未設置過狀態的用戶應該返回離線
        assert UserStatusEvent.get_user_status("unknown_user") == UserStatus.OFFLINE

    async def test_user_connected_and_disconnected(self):
        """測試用戶連線和斷線狀態追蹤"""
        user_id = "conn_user"
        username = "connection_test"

        # 訂閱狀態變更
        queue = UserStatusEvent.subscribe()

        # 用戶第一次連線 - 應該發送 ONLINE
        await UserStatusEvent.user_connected(user_id, username)
        status_change = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert status_change.status == UserStatus.ONLINE
        assert UserStatusEvent.get_user_status(user_id) == UserStatus.ONLINE

        # 用戶第二次連線（多分頁）- 不應該發送新狀態
        await UserStatusEvent.user_connected(user_id, username)
        # queue 應該是空的（沒有新事件）
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.1)

        # 用戶關閉一個分頁 - 不應該發送 OFFLINE
        await UserStatusEvent.user_disconnected(user_id)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.1)

        # 用戶關閉最後一個分頁 - 應該發送 OFFLINE
        await UserStatusEvent.user_disconnected(user_id)
        status_change = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert status_change.status == UserStatus.OFFLINE
        assert UserStatusEvent.get_user_status(user_id) == UserStatus.OFFLINE

        # 清理
        UserStatusEvent.unsubscribe(queue)

    async def test_get_online_users(self):
        """測試獲取在線用戶列表"""
        # 設置一些用戶狀態
        await UserStatusEvent.user_connected("online1", "user1")
        await UserStatusEvent.user_connected("online2", "user2")

        # 獲取在線用戶列表
        online_users = UserStatusEvent.get_online_users()
        assert "online1" in online_users
        assert "online2" in online_users

        # 用戶離線後應該從列表中移除
        await UserStatusEvent.user_disconnected("online1")
        online_users = UserStatusEvent.get_online_users()
        assert "online1" not in online_users
        assert "online2" in online_users

    async def test_get_online_users_query_resolver(self):
        """測試 get_online_users GraphQL query resolver 返回 OnlineUserInfo 列表"""
        # 清理之前的狀態
        UserStatusEvent._user_status.clear()
        UserStatusEvent._user_connections.clear()
        UserStatusEvent._user_info.clear()

        # 設置一些用戶為在線狀態
        await UserStatusEvent.user_connected("query_user1", "alice")
        await UserStatusEvent.user_connected("query_user2", "bob")

        # 使用 mock info 呼叫 resolver
        class MockInfo:
            pass

        result = get_online_users(MockInfo())

        # 驗證返回類型和內容
        assert len(result) == 2
        assert all(isinstance(item, OnlineUserInfo) for item in result)

        user_ids = [str(item.user_id) for item in result]
        usernames = [item.username for item in result]

        assert "query_user1" in user_ids
        assert "query_user2" in user_ids
        assert "alice" in usernames
        assert "bob" in usernames

        # 清理測試狀態
        await UserStatusEvent.user_disconnected("query_user1")
        await UserStatusEvent.user_disconnected("query_user2")