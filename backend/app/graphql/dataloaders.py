"""
DataLoader 實作用於解決 N+1 查詢問題
"""

from typing import List, Dict, Optional
from collections import defaultdict
from strawberry.dataloader import DataLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.like import Like
from app.models.follow import Follow


class UserLoader(DataLoader):
    """批次載入用戶資料的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_users)
        self.session = session

    async def batch_load_users(self, user_ids: List[int]) -> List[Optional[User]]:
        """批次載入多個用戶"""
        # 單一查詢獲取所有需要的用戶
        result = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = result.scalars().all()

        # 建立 id -> user 的映射
        user_map: Dict[int, User] = {user.id: user for user in users}

        # 按照請求的順序返回結果
        return [user_map.get(user_id) for user_id in user_ids]


class PostLoader(DataLoader):
    """批次載入文章資料的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_posts)
        self.session = session

    async def batch_load_posts(self, post_ids: List[int]) -> List[Optional[Post]]:
        """批次載入多個文章"""
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.tags))  # 預載入標籤
            .where(Post.id.in_(post_ids))
        )
        posts = result.scalars().all()

        post_map: Dict[int, Post] = {post.id: post for post in posts}
        return [post_map.get(post_id) for post_id in post_ids]


class CommentLoader(DataLoader):
    """批次載入評論資料的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_comments)
        self.session = session

    async def batch_load_comments(self, comment_ids: List[int]) -> List[Optional[Comment]]:
        """批次載入多個評論"""
        result = await self.session.execute(
            select(Comment)
            .options(selectinload(Comment.author))  # 預載入作者
            .where(Comment.id.in_(comment_ids))
        )
        comments = result.scalars().all()

        comment_map: Dict[int, Comment] = {comment.id: comment for comment in comments}
        return [comment_map.get(comment_id) for comment_id in comment_ids]


class PostCommentsLoader(DataLoader):
    """批次載入文章評論的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_post_comments)
        self.session = session

    async def batch_load_post_comments(self, post_ids: List[int]) -> List[List[Comment]]:
        """批次載入多篇文章的評論"""
        result = await self.session.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.post_id.in_(post_ids))
            .where(Comment.deleted_at.is_(None))  # 排除已刪除的評論
            .order_by(Comment.created_at.asc())  # 改為升序，最早的評論在前
        )
        comments = result.scalars().all()

        # 建立 post_id -> comments 的映射
        comments_map: Dict[int, List[Comment]] = defaultdict(list)
        for comment in comments:
            comments_map[comment.post_id].append(comment)

        # 按照請求的順序返回結果
        return [comments_map.get(post_id, []) for post_id in post_ids]


class LikeCountLoader(DataLoader):
    """批次載入按讚數的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_like_counts)
        self.session = session

    async def batch_load_like_counts(self, post_ids: List[int]) -> List[int]:
        """批次載入多篇文章的按讚數"""
        from sqlalchemy import func

        result = await self.session.execute(
            select(Like.post_id, func.count(Like.id).label("count"))
            .where(Like.post_id.in_(post_ids))
            .group_by(Like.post_id)
        )

        # 建立 post_id -> count 的映射
        count_map: Dict[int, int] = {row.post_id: row.count for row in result}

        # 按照請求的順序返回結果（沒有按讚的文章返回 0）
        return [count_map.get(post_id, 0) for post_id in post_ids]


class UserLikedPostsLoader(DataLoader):
    """批次載入用戶是否按讚文章的 DataLoader"""

    def __init__(self, session: AsyncSession, user_id: Optional[int]):
        super().__init__(load_fn=self.batch_load_user_liked_posts)
        self.session = session
        self.user_id = user_id

    async def batch_load_user_liked_posts(self, post_ids: List[int]) -> List[bool]:
        """批次檢查用戶是否按讚了多篇文章"""
        if not self.user_id:
            return [False] * len(post_ids)

        result = await self.session.execute(
            select(Like.post_id)
            .where(Like.user_id == self.user_id)
            .where(Like.post_id.in_(post_ids))
        )
        liked_post_ids = set(result.scalars().all())

        # 按照請求的順序返回結果
        return [post_id in liked_post_ids for post_id in post_ids]


class FollowersCountLoader(DataLoader):
    """批次載入追蹤者數量的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_followers_count)
        self.session = session

    async def batch_load_followers_count(self, user_ids: List[int]) -> List[int]:
        """批次載入多個用戶的追蹤者數量"""
        from sqlalchemy import func

        result = await self.session.execute(
            select(Follow.followed_id, func.count(Follow.id).label("count"))
            .where(Follow.followed_id.in_(user_ids))
            .group_by(Follow.followed_id)
        )

        count_map: Dict[int, int] = {row.followed_id: row.count for row in result}
        return [count_map.get(user_id, 0) for user_id in user_ids]


class FollowingCountLoader(DataLoader):
    """批次載入追蹤中數量的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_following_count)
        self.session = session

    async def batch_load_following_count(self, user_ids: List[int]) -> List[int]:
        """批次載入多個用戶的追蹤中數量"""
        from sqlalchemy import func

        result = await self.session.execute(
            select(Follow.follower_id, func.count(Follow.id).label("count"))
            .where(Follow.follower_id.in_(user_ids))
            .group_by(Follow.follower_id)
        )

        count_map: Dict[int, int] = {row.follower_id: row.count for row in result}
        return [count_map.get(user_id, 0) for user_id in user_ids]


class DataLoaderContext:
    """DataLoader 上下文管理器"""

    def __init__(self, session: AsyncSession, user_id: Optional[int] = None):
        self.session = session
        self.user_id = user_id

        # 初始化所有 DataLoader
        self.user_loader = UserLoader(session)
        self.post_loader = PostLoader(session)
        self.comment_loader = CommentLoader(session)
        self.post_comments_loader = PostCommentsLoader(session)
        self.like_count_loader = LikeCountLoader(session)
        self.user_liked_posts_loader = UserLikedPostsLoader(session, user_id)
        self.followers_count_loader = FollowersCountLoader(session)
        self.following_count_loader = FollowingCountLoader(session)

    def get_user_loader(self) -> UserLoader:
        return self.user_loader

    def get_post_loader(self) -> PostLoader:
        return self.post_loader

    def get_comment_loader(self) -> CommentLoader:
        return self.comment_loader

    def get_post_comments_loader(self) -> PostCommentsLoader:
        return self.post_comments_loader

    def get_like_count_loader(self) -> LikeCountLoader:
        return self.like_count_loader

    def get_user_liked_posts_loader(self) -> UserLikedPostsLoader:
        return self.user_liked_posts_loader

    def get_followers_count_loader(self) -> FollowersCountLoader:
        return self.followers_count_loader

    def get_following_count_loader(self) -> FollowingCountLoader:
        return self.following_count_loader