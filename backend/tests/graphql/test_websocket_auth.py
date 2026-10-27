"""
WebSocket 訂閱的身分認證，走真正的 WebSocket 連線（graphql-transport-ws 協定）

瀏覽器的 WebSocket API 不能自訂 headers，前端（frontend/src/client.ts）改把 token 放在
connectionParams，也就是 connection_init 訊息的 payload。這條路徑要靠 strawberry 把 payload
交給 context.connection_params，只直接呼叫 resolver 的單元測試驗證不到。
"""
import asyncio
from datetime import datetime

import pytest
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.graphql.subscriptions.followed_user_post import FollowedUserPostEvent
from app.graphql.types.post import PostType
from app.main import app
from app.models.post import PostStatus

USER_ID = 42
SUBSCRIPTION = "subscription { followedUserPosted { title } }"


def bearer_token() -> str:
    return f"Bearer {create_access_token(data={'sub': str(USER_ID)})}"


def make_post() -> PostType:
    now = datetime.now()
    return PostType(
        id=1, title="追蹤對象的新文章", slug="new-post", content="內容",
        status=PostStatus.PUBLISHED, author_id=7,
        created_at=now, updated_at=now, published_at=now,
    )


async def wait_until_subscribed(user_id: int):
    """在伺服器的事件迴圈裡等訂閱註冊完成，之後發布的文章才收得到"""
    async def poll():
        while user_id not in FollowedUserPostEvent._subscribers:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), timeout=2)


def open_subscription(ws, connection_params: dict):
    ws.send_json({"type": "connection_init", "payload": connection_params})
    assert ws.receive_json()["type"] == "connection_ack"
    ws.send_json({"id": "1", "type": "subscribe", "payload": {"query": SUBSCRIPTION}})


@pytest.mark.parametrize("connection_params, headers", [
    pytest.param({"Authorization": bearer_token()}, {}, id="connectionParams（前端的寫法）"),
    pytest.param({"authorization": bearer_token()}, {}, id="connectionParams 小寫鍵"),
    pytest.param({}, {"Authorization": bearer_token()}, id="handshake header（非瀏覽器客戶端）"),
])
def test_authenticated_subscriber_receives_followed_user_post(connection_params, headers):
    with TestClient(app).websocket_connect(
        "/graphql", subprotocols=["graphql-transport-ws"], headers=headers
    ) as ws:
        open_subscription(ws, connection_params)
        ws.portal.call(wait_until_subscribed, USER_ID)

        ws.portal.call(FollowedUserPostEvent.publish_to_followers, [USER_ID], make_post())

        message = ws.receive_json()
        assert message == {
            "id": "1",
            "type": "next",
            "payload": {"data": {"followedUserPosted": {"title": "追蹤對象的新文章"}}},
        }


def test_subscription_without_token_is_rejected():
    with TestClient(app).websocket_connect("/graphql", subprotocols=["graphql-transport-ws"]) as ws:
        open_subscription(ws, {})

        message = ws.receive_json()

    assert message == {
        "id": "1",
        "type": "next",
        "payload": {"data": None, "errors": [{"message": "Authentication required"}]},
    }
