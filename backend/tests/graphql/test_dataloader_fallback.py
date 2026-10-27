"""
沒有 DataLoader 時的 fallback

直接執行 schema、傳不含 dataloaders 的 dict 當 context 時（例如
test_dataloader_performance_comparison.py 的對照組），欄位改為逐筆查詢資料庫。
正式環境的 GraphQLContext 一定提供 DataLoader，所以這裡用同一組資料、同一個查詢，
確認兩條路徑的結果都和預期完全相同。
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.graphql.dataloaders import DataLoaderContext
from app.graphql.schema import schema
from app.models.comment import Comment
from app.models.follow import Follow
from app.models.post import Post, PostStatus
from app.models.tag import Tag
from tests.factories import UserFactory

USER_QUERY = """
query User($id: Int!) {
    user(id: $id) {
        followersCount
        followingCount
        followers { username }
        following { username }
        isFollowedByMe
    }
}
"""

SEARCH_QUERY = """
{
    search(term: "fallback") {
        ... on PostType { title author { username } tags { name } totalComments }
    }
}
"""


@pytest.fixture
async def social_graph(test_session):
    """
    alice 與 bob、carol、dave 互相追蹤：和 bob 是很久以前，和 carol、dave 是同一時間
    （carol 先建立），用來區分排序的 created_at 與次要的 id。
    alice、bob 各有一篇文章，alice 的文章有兩則留言與一則已刪除的留言。
    """
    users = {name: await UserFactory.create(test_session, username=name)
             for name in ("alice", "bob", "carol", "dave")}
    alice = users["alice"]
    now = datetime.now(timezone.utc)
    long_ago = now - timedelta(days=2)
    for name, created_at in (("bob", long_ago), ("carol", now), ("dave", now)):
        test_session.add_all([
            Follow(follower_id=users[name].id, followed_id=alice.id, created_at=created_at),
            Follow(follower_id=alice.id, followed_id=users[name].id, created_at=created_at),
        ])
        await test_session.flush()  # 依序寫入，id 才會照順序遞增

    first = Post(title="fallback one", slug="fallback-one", content="content",
                 status=PostStatus.PUBLISHED, author_id=alice.id,
                 tags=[Tag(name="python", slug="python"), Tag(name="graphql", slug="graphql")])
    second = Post(title="fallback two", slug="fallback-two", content="content",
                  status=PostStatus.PUBLISHED, author_id=users["bob"].id,
                  tags=[Tag(name="rust", slug="rust")])
    test_session.add_all([first, second])
    await test_session.flush()
    test_session.add_all([
        Comment(content="留言", user_id=users["bob"].id, post_id=first.id),
        Comment(content="留言", user_id=users["carol"].id, post_id=first.id),
        Comment(content="已刪除", user_id=users["dave"].id, post_id=first.id, deleted_at=now),
    ])
    await test_session.commit()
    ids = {name: user.id for name, user in users.items()}
    # 模擬新的請求：測試建立的物件（例如已經載入的 tags）不能留在 identity map 裡，
    # 否則 fallback 少了 selectinload 也不會出錯
    test_session.expunge_all()
    return ids


def make_context(session, viewer_id, with_dataloaders):
    context = {"db_session": session, "user_id": viewer_id}
    if with_dataloaders:
        context["dataloaders"] = DataLoaderContext(session, viewer_id)
    return context


@pytest.mark.asyncio
@pytest.mark.parametrize("with_dataloaders", [False, True], ids=["fallback", "dataloader"])
async def test_user_follow_fields(test_session, social_graph, with_dataloaders):
    """以 carol 的身分查詢：carol 追蹤 alice，沒有追蹤 bob"""
    context = make_context(test_session, social_graph["carol"], with_dataloaders)

    data = {}
    for name in ("alice", "bob"):
        result = await schema.execute(
            USER_QUERY, variable_values={"id": social_graph[name]}, context_value=context
        )
        assert result.errors is None
        data[name] = result.data["user"]

    newest_first = [{"username": "dave"}, {"username": "carol"}, {"username": "bob"}]
    assert data == {
        "alice": {
            "followersCount": 3,
            "followingCount": 3,
            "followers": newest_first,
            "following": newest_first,
            "isFollowedByMe": True,
        },
        "bob": {
            "followersCount": 1,
            "followingCount": 1,
            "followers": [{"username": "alice"}],
            "following": [{"username": "alice"}],
            "isFollowedByMe": False,
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("with_dataloaders", [False, True], ids=["fallback", "dataloader"])
async def test_search_post_fields(test_session, social_graph, with_dataloaders):
    """搜尋結果沒有預載作者與標籤，靠 fallback 或 DataLoader 載入"""
    context = make_context(test_session, None, with_dataloaders)

    result = await schema.execute(SEARCH_QUERY, context_value=context)

    assert result.errors is None
    posts = sorted(result.data["search"], key=lambda post: post["title"])
    for post in posts:
        post["tags"] = sorted(post["tags"], key=lambda tag: tag["name"])
    assert posts == [
        {
            "title": "fallback one",
            "author": {"username": "alice"},
            "tags": [{"name": "graphql"}, {"name": "python"}],
            "totalComments": 2,
        },
        {
            "title": "fallback two",
            "author": {"username": "bob"},
            "tags": [{"name": "rust"}],
            "totalComments": 0,
        },
    ]


@pytest.mark.asyncio
async def test_is_followed_by_me_without_viewer(test_session, social_graph):
    """沒有登入時 isFollowedByMe 一律是 False，不需要查資料庫"""
    context = make_context(test_session, None, with_dataloaders=False)

    result = await schema.execute(
        USER_QUERY, variable_values={"id": social_graph["alice"]}, context_value=context
    )

    assert result.errors is None
    assert result.data["user"]["isFollowedByMe"] is False
