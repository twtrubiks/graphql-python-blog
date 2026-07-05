"""追蹤功能 DataLoader 測試（followers / following / isFollowedByMe 的 N+1 修復）"""
import asyncio

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow import Follow
import app.graphql.dataloaders as dataloaders_module
from app.graphql.dataloaders import (
    FollowersLoader,
    FollowingLoader,
    IsFollowedByUserLoader,
)


@pytest.mark.asyncio
class TestFollowListLoaders:
    """FollowersLoader / FollowingLoader 批次載入測試"""

    async def test_followers_loader_batches(self, test_session: AsyncSession, user_factory):
        """多個 key 一次批次載入，各 key 回傳正確的追蹤者"""
        user_a = await user_factory.create()
        user_b = await user_factory.create()
        user_c = await user_factory.create()

        # b, c 追蹤 a；a 追蹤 b
        test_session.add(Follow(follower_id=user_b.id, followed_id=user_a.id))
        test_session.add(Follow(follower_id=user_c.id, followed_id=user_a.id))
        test_session.add(Follow(follower_id=user_a.id, followed_id=user_b.id))
        await test_session.commit()

        loader = FollowersLoader(test_session)
        followers_a, followers_b, followers_c = await asyncio.gather(
            loader.load(user_a.id),
            loader.load(user_b.id),
            loader.load(user_c.id),
        )

        assert {u.id for u in followers_a} == {user_b.id, user_c.id}
        assert [u.id for u in followers_b] == [user_a.id]
        assert followers_c == []

    async def test_following_loader_batches(self, test_session: AsyncSession, user_factory):
        """多個 key 一次批次載入，各 key 回傳正確的追蹤中列表"""
        user_a = await user_factory.create()
        user_b = await user_factory.create()
        user_c = await user_factory.create()

        # a 追蹤 b, c；b 追蹤 c
        test_session.add(Follow(follower_id=user_a.id, followed_id=user_b.id))
        test_session.add(Follow(follower_id=user_a.id, followed_id=user_c.id))
        test_session.add(Follow(follower_id=user_b.id, followed_id=user_c.id))
        await test_session.commit()

        loader = FollowingLoader(test_session)
        following_a, following_b, following_c = await asyncio.gather(
            loader.load(user_a.id),
            loader.load(user_b.id),
            loader.load(user_c.id),
        )

        assert {u.id for u in following_a} == {user_b.id, user_c.id}
        assert [u.id for u in following_b] == [user_c.id]
        assert following_c == []

    async def test_follow_list_limit(self, test_session: AsyncSession, user_factory, monkeypatch):
        """每個用戶的 followers / following 列表有載入上限"""
        monkeypatch.setattr(dataloaders_module, "FOLLOW_LIST_LIMIT", 3)

        target = await user_factory.create()
        followers = [await user_factory.create() for _ in range(5)]
        for follower in followers:
            test_session.add(Follow(follower_id=follower.id, followed_id=target.id))
        await test_session.commit()

        loader = FollowersLoader(test_session)
        result = await loader.load(target.id)
        assert len(result) == 3

        # following 方向也一樣有上限
        source = await user_factory.create()
        for followed in followers:
            test_session.add(Follow(follower_id=source.id, followed_id=followed.id))
        await test_session.commit()

        following_loader = FollowingLoader(test_session)
        result = await following_loader.load(source.id)
        assert len(result) == 3


@pytest.mark.asyncio
class TestIsFollowedByUserLoader:
    """IsFollowedByUserLoader 批次載入測試"""

    async def test_is_followed_loader(self, test_session: AsyncSession, user_factory):
        """已追蹤回傳 True，未追蹤回傳 False"""
        me = await user_factory.create()
        followed = await user_factory.create()
        not_followed = await user_factory.create()

        test_session.add(Follow(follower_id=me.id, followed_id=followed.id))
        await test_session.commit()

        loader = IsFollowedByUserLoader(test_session, me.id)
        results = await asyncio.gather(
            loader.load(followed.id),
            loader.load(not_followed.id),
        )
        assert results == [True, False]

    async def test_is_followed_loader_anonymous(self, test_session: AsyncSession, user_factory):
        """未登入（user_id=None）一律回傳 False，且不查資料庫"""
        someone = await user_factory.create()

        loader = IsFollowedByUserLoader(test_session, None)
        assert await loader.load(someone.id) is False


@pytest.mark.asyncio
class TestFollowFieldsNoNPlusOne:
    """透過 GraphQL 驗證 followers / following / isFollowedByMe 不會產生 N+1 查詢"""

    async def test_users_follow_fields_sql_count(
        self, authenticated_client, test_engine, test_session: AsyncSession, test_user, user_factory
    ):
        """查詢多個用戶的 follow 欄位時，SQL 查詢數應為常數而非隨用戶數線性成長"""
        users = [await user_factory.create() for _ in range(4)]

        # 建立交錯的追蹤關係
        for i, user in enumerate(users):
            test_session.add(Follow(follower_id=user.id, followed_id=users[(i + 1) % len(users)].id))
            test_session.add(Follow(follower_id=test_user.id, followed_id=user.id))
        await test_session.commit()

        query = """
        query {
            users(limit: 20) {
                id
                followers { username }
                following { username }
                isFollowedByMe
            }
        }
        """

        select_statements = []

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                select_statements.append(statement)

        event.listen(test_engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = await authenticated_client.post("/graphql", json={"query": query})
        finally:
            event.remove(test_engine.sync_engine, "before_cursor_execute", before_cursor_execute)

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert len(data["data"]["users"]) >= 5  # test_user + 4 個新用戶

        # 有 DataLoader 時：1(users) + 1(followers) + 1(following) + 1(isFollowed) ≈ 4 次
        # 沒有 DataLoader 時會是 ~1 + N*2 + N*2 + N*2 次，遠超過這個上限
        assert len(select_statements) <= 6, (
            f"預期批次查詢（<=6 次 SELECT），實際執行 {len(select_statements)} 次"
        )

        # isFollowedByMe 結果正確性抽查：test_user 追蹤了所有新用戶
        by_id = {u["id"]: u for u in data["data"]["users"]}
        for user in users:
            assert by_id[str(user.id)]["isFollowedByMe"] is True
