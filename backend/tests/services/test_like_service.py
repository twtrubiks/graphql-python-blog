"""沒有 DataLoader 時，likesCount / isLiked 改用 LikeService 直接查詢"""
import pytest

from app.models.like import Like
from app.services.like import LikeService
from tests.factories import PostFactory, UserFactory
from tests.utils import insert_after_existence_check


@pytest.fixture
async def liked_posts(test_session):
    """popular 被 alice、bob 按讚，other 只被 bob 按讚，quiet 沒有人按讚"""
    alice = await UserFactory.create(test_session, username="alice")
    bob = await UserFactory.create(test_session, username="bob")
    posts = {
        title: await PostFactory.create(test_session, author_id=alice.id, title=title)
        for title in ("popular", "other", "quiet")
    }
    test_session.add_all([
        Like(user_id=alice.id, post_id=posts["popular"].id),
        Like(user_id=bob.id, post_id=posts["popular"].id),
        Like(user_id=bob.id, post_id=posts["other"].id),
    ])
    await test_session.commit()
    return {"alice": alice, "bob": bob, **posts}


@pytest.mark.asyncio
async def test_get_post_likes_count(test_session, liked_posts):
    counts = [
        await LikeService.get_post_likes_count(test_session, liked_posts[title].id)
        for title in ("popular", "other", "quiet")
    ]

    assert counts == [2, 1, 0]


@pytest.mark.asyncio
@pytest.mark.parametrize("username, title, expected", [
    ("alice", "popular", True),
    ("alice", "other", False),
    ("bob", "other", True),
])
async def test_is_post_liked_by_user(test_session, liked_posts, username, title, expected):
    liked = await LikeService.is_post_liked_by_user(
        test_session, liked_posts[title].id, liked_posts[username].id
    )

    assert liked is expected


@pytest.mark.asyncio
async def test_anonymous_user_has_not_liked(test_session, liked_posts):
    assert await LikeService.is_post_liked_by_user(test_session, liked_posts["popular"].id, None) is False


@pytest.mark.asyncio
async def test_like_post_race_is_blocked_by_unique_constraint(test_session, test_engine, monkeypatch):
    """同一個用戶同時送出兩次按讚：兩邊都查不到既有的讚，後寫入的那個要回報已按讚，而不是拋出錯誤"""
    user = await UserFactory.create(test_session)
    post = await PostFactory.create(test_session, author_id=user.id)
    await test_session.commit()
    user_id, post_id = user.id, post.id  # rollback 會讓 ORM 物件過期，之後不能再讀屬性
    insert_after_existence_check(monkeypatch, test_session, test_engine, Like(user_id=user_id, post_id=post_id))

    result = await LikeService.like_post(test_session, post_id, user_id)

    assert result == (False, "您已經按讚過這篇文章")
    # rollback 之後 session 還能繼續使用，而且只有一筆讚
    assert await LikeService.get_post_likes_count(test_session, post_id) == 1


@pytest.mark.asyncio
async def test_like_post_ignores_other_likes(test_session, liked_posts):
    """other 已被 bob 按讚、alice 按讚過 popular：都不能讓 alice 按讚 other 被誤判為「已經按讚過」"""
    alice_id, other_id = liked_posts["alice"].id, liked_posts["other"].id

    result = await LikeService.like_post(test_session, other_id, alice_id)

    assert result == (True, "按讚成功")
    assert await LikeService.get_post_likes_count(test_session, other_id) == 2

