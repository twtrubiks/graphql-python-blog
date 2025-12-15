"""PostService 擴展功能測試

測試 get_posts_by_followed_users 方法
"""

import pytest
from datetime import datetime, timezone, timedelta
from tests.factories import UserFactory, PostFactory
from app.services.post import PostService
from app.models.follow import Follow
from app.models.post import PostStatus


class TestGetPostsByFollowedUsers:
    """測試 PostService.get_posts_by_followed_users 方法"""

    @pytest.mark.asyncio
    async def test_get_posts_by_followed_users_success(self, test_session):
        """測試成功獲取追蹤用戶的文章"""
        # Arrange: 建立用戶
        user1 = await UserFactory.create(test_session, username="follower")
        user2 = await UserFactory.create(test_session, username="followed_author1")
        user3 = await UserFactory.create(test_session, username="followed_author2")

        # user1 追蹤 user2 和 user3
        test_session.add_all([
            Follow(follower_id=user1.id, followed_id=user2.id),
            Follow(follower_id=user1.id, followed_id=user3.id)
        ])

        # user2 和 user3 各發布一篇文章
        post1 = await PostFactory.create(
            test_session,
            author_id=user2.id,
            title="Post by user2",
            status=PostStatus.PUBLISHED
        )
        post2 = await PostFactory.create(
            test_session,
            author_id=user3.id,
            title="Post by user3",
            status=PostStatus.PUBLISHED
        )

        await test_session.commit()

        # Act
        posts, total_count = await PostService.get_posts_by_followed_users(
            test_session, user1.id, page=1, limit=10
        )

        # Assert
        assert total_count == 2
        assert len(posts) == 2
        post_titles = [p.title for p in posts]
        assert "Post by user2" in post_titles
        assert "Post by user3" in post_titles

    @pytest.mark.asyncio
    async def test_get_posts_by_followed_users_no_following(self, test_session):
        """測試沒有追蹤任何人時返回空列表"""
        # Arrange
        user = await UserFactory.create(test_session, username="lonely_user")
        await test_session.commit()

        # Act
        posts, total_count = await PostService.get_posts_by_followed_users(
            test_session, user.id, page=1, limit=10
        )

        # Assert
        assert total_count == 0
        assert posts == []

    @pytest.mark.asyncio
    async def test_get_posts_by_followed_users_excludes_unfollowed(self, test_session):
        """測試不會返回未追蹤用戶的文章"""
        # Arrange
        user1 = await UserFactory.create(test_session, username="follower_user")
        user2 = await UserFactory.create(test_session, username="followed_user")
        user3 = await UserFactory.create(test_session, username="not_followed_user")

        # user1 只追蹤 user2，不追蹤 user3
        test_session.add(Follow(follower_id=user1.id, followed_id=user2.id))

        # user2 和 user3 都發布文章
        post1 = await PostFactory.create(
            test_session,
            author_id=user2.id,
            title="Followed user post",
            status=PostStatus.PUBLISHED
        )
        post2 = await PostFactory.create(
            test_session,
            author_id=user3.id,
            title="Not followed user post",
            status=PostStatus.PUBLISHED
        )

        await test_session.commit()

        # Act
        posts, total_count = await PostService.get_posts_by_followed_users(
            test_session, user1.id, page=1, limit=10
        )

        # Assert: 只應該有 user2 的文章
        assert total_count == 1
        assert len(posts) == 1
        assert posts[0].title == "Followed user post"

    @pytest.mark.asyncio
    async def test_get_posts_by_followed_users_excludes_draft(self, test_session):
        """測試不會返回草稿文章"""
        # Arrange
        user1 = await UserFactory.create(test_session, username="follower_u")
        user2 = await UserFactory.create(test_session, username="author_u")

        test_session.add(Follow(follower_id=user1.id, followed_id=user2.id))

        # user2 發布一篇文章和一篇草稿
        published_post = await PostFactory.create(
            test_session,
            author_id=user2.id,
            title="Published post",
            status=PostStatus.PUBLISHED
        )
        draft_post = await PostFactory.create(
            test_session,
            author_id=user2.id,
            title="Draft post",
            status=PostStatus.DRAFT
        )

        await test_session.commit()

        # Act
        posts, total_count = await PostService.get_posts_by_followed_users(
            test_session, user1.id, page=1, limit=10
        )

        # Assert: 只應該有已發布的文章
        assert total_count == 1
        assert len(posts) == 1
        assert posts[0].title == "Published post"

    @pytest.mark.asyncio
    async def test_get_posts_by_followed_users_pagination(self, test_session):
        """測試分頁功能"""
        # Arrange
        user1 = await UserFactory.create(test_session, username="paginated_follower")
        user2 = await UserFactory.create(test_session, username="prolific_author")

        test_session.add(Follow(follower_id=user1.id, followed_id=user2.id))

        # user2 發布 5 篇文章
        now = datetime.now(timezone.utc)
        for i in range(5):
            await PostFactory.create(
                test_session,
                author_id=user2.id,
                title=f"Post {i+1}",
                status=PostStatus.PUBLISHED,
                created_at=now - timedelta(days=i)
            )

        await test_session.commit()

        # Act: 獲取第一頁（2 篇）
        posts_page1, total_count = await PostService.get_posts_by_followed_users(
            test_session, user1.id, page=1, limit=2
        )

        # Assert
        assert total_count == 5
        assert len(posts_page1) == 2

        # Act: 獲取第二頁（2 篇）
        posts_page2, _ = await PostService.get_posts_by_followed_users(
            test_session, user1.id, page=2, limit=2
        )

        # Assert
        assert len(posts_page2) == 2

        # 確認第一頁和第二頁的文章不重複
        page1_ids = {p.id for p in posts_page1}
        page2_ids = {p.id for p in posts_page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_get_posts_by_followed_users_order_by_created_at(self, test_session):
        """測試文章按創建時間倒序排列"""
        # Arrange
        user1 = await UserFactory.create(test_session, username="order_follower")
        user2 = await UserFactory.create(test_session, username="order_author")

        test_session.add(Follow(follower_id=user1.id, followed_id=user2.id))

        # 建立不同時間的文章
        now = datetime.now(timezone.utc)
        old_post = await PostFactory.create(
            test_session,
            author_id=user2.id,
            title="Old post",
            status=PostStatus.PUBLISHED,
            created_at=now - timedelta(days=2)
        )
        new_post = await PostFactory.create(
            test_session,
            author_id=user2.id,
            title="New post",
            status=PostStatus.PUBLISHED,
            created_at=now
        )

        await test_session.commit()

        # Act
        posts, _ = await PostService.get_posts_by_followed_users(
            test_session, user1.id, page=1, limit=10
        )

        # Assert: 最新的文章應該在前面
        assert len(posts) == 2
        assert posts[0].title == "New post"
        assert posts[1].title == "Old post"
