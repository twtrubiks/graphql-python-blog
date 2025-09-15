import pytest
import asyncio
from datetime import datetime
from app.graphql.subscriptions.user_status import (
    UserStatusEvent, 
    UserStatusSubscription, 
    UserStatus,
    UserStatusChange
)


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
        
        # 開始訂閱
        subscription_gen = subscription.user_status_changed()
        
        # 在另一個協程中發布狀態變更
        async def publish_status_changes():
            await asyncio.sleep(0.1)
            await UserStatusEvent.publish_status_change(
                user_id="user1",
                username="alice",
                status=UserStatus.ONLINE
            )
        
        # 啟動發布任務
        publish_task = asyncio.create_task(publish_status_changes())
        
        # 從 subscription 獲取狀態變更
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