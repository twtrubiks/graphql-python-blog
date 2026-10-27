"""除錯時在 log 與 shell 看到的 model 字串"""
from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post, PostStatus
from app.models.user import User


def test_user_repr():
    user = User(id=1, username="alice", email="alice@example.com")

    assert repr(user) == "<User(id=1, username='alice', email='alice@example.com')>"


def test_post_repr_truncates_long_title():
    assert repr(Post(id=2, title="a" * 30, status=PostStatus.DRAFT)) == f"<Post(id=2, title='{'a' * 30}', status=PostStatus.DRAFT)>"
    assert repr(Post(id=3, title="b" * 31, status=PostStatus.PUBLISHED)) == f"<Post(id=3, title='{'b' * 30}', status=PostStatus.PUBLISHED)>"


def test_comment_repr():
    assert repr(Comment(id=4, post_id=2, user_id=1)) == "<Comment(id=4, post_id=2, user_id=1)>"


def test_like_repr():
    assert repr(Like(id=5, user_id=1, post_id=2)) == "<Like(id=5, user_id=1, post_id=2)>"
