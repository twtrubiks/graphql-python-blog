"""
DataLoader 實作 - 解決 GraphQL N+1 查詢問題的關鍵

什麼是 N+1 問題？
當查詢 N 篇文章的作者時，如果不使用 DataLoader：
- 1 次查詢獲取 N 篇文章
- N 次查詢獲取每篇文章的作者
- 總共 N+1 次資料庫查詢

使用 DataLoader 後：
- 1 次查詢獲取 N 篇文章
- 1 次批次查詢獲取所有作者
- 總共只需要 2 次查詢！

DataLoader 的核心機制：
1. 收集（Batching）：在單個事件循環中收集所有查詢需求
2. 去重（Deduplication）：自動去除重複的查詢
3. 快取（Caching）：在請求週期內快取結果
4. 批次執行：一次性執行所有查詢

教學重點：
- 每個 DataLoader 對應一種資源類型
- load_fn 必須返回與輸入順序一致的結果
- DataLoader 是請求級別的，每個請求創建新實例
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
from app.models.tag import Tag, post_tags


class UserLoader(DataLoader):
    """
    批次載入用戶資料的 DataLoader

    範例場景：
    當查詢 10 篇文章，每篇文章都需要作者資訊時，
    GraphQL 會自動收集所有作者 ID，然後呼叫這個 loader 一次性載入。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_users)
        self.session = session

    async def batch_load_users(self, user_ids: List[int]) -> List[Optional[User]]:
        """
        批次載入多個用戶

        關鍵點：
        1. 接收多個 ID，執行單一查詢
        2. 必須保持返回順序與輸入順序一致
        3. 找不到的 ID 返回 None
        """
        # 單一查詢獲取所有需要的用戶（避免 N+1）
        result = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = result.scalars().all()

        # 建立 id -> user 的映射（快速查找）
        user_map: Dict[int, User] = {user.id: user for user in users}

        # 關鍵：按照請求的順序返回結果，這是 DataLoader 的要求
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


class CommentCountLoader(DataLoader):
    """批次載入評論數的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_comment_counts)
        self.session = session

    async def batch_load_comment_counts(self, post_ids: List[int]) -> List[int]:
        """批次載入多篇文章的評論數（排除已軟刪除的評論）"""
        from sqlalchemy import func

        result = await self.session.execute(
            select(Comment.post_id, func.count(Comment.id).label("count"))
            .where(Comment.post_id.in_(post_ids))
            .where(Comment.deleted_at.is_(None))
            .group_by(Comment.post_id)
        )

        # 建立 post_id -> count 的映射
        count_map: Dict[int, int] = {row.post_id: row.count for row in result}

        # 按照請求的順序返回結果（沒有評論的文章返回 0）
        return [count_map.get(post_id, 0) for post_id in post_ids]


class PostTagsLoader(DataLoader):
    """批次載入文章標籤的 DataLoader"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_post_tags)
        self.session = session

    async def batch_load_post_tags(self, post_ids: List[int]) -> List[List[Tag]]:
        """批次載入多篇文章的標籤"""
        result = await self.session.execute(
            select(post_tags.c.post_id, Tag)
            .join(Tag, Tag.id == post_tags.c.tag_id)
            .where(post_tags.c.post_id.in_(post_ids))
        )

        # 建立 post_id -> tags 的映射
        tags_map: Dict[int, List[Tag]] = defaultdict(list)
        for post_id, tag in result:
            tags_map[post_id].append(tag)

        # 按照請求的順序返回結果
        return [tags_map.get(post_id, []) for post_id in post_ids]


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


# followers / following 列表每個用戶的載入上限，避免巨量追蹤者一次全部載入
FOLLOW_LIST_LIMIT = 100


class FollowersLoader(DataLoader):
    """批次載入追蹤者列表的 DataLoader（每個用戶最多 FOLLOW_LIST_LIMIT 個）"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_followers)
        self.session = session

    async def batch_load_followers(self, user_ids: List[int]) -> List[List[User]]:
        """批次載入多個用戶的追蹤者，用 window function 在 SQL 端對每個用戶套用上限"""
        from sqlalchemy import func

        rn = func.row_number().over(
            partition_by=Follow.followed_id,
            order_by=(Follow.created_at.desc(), Follow.id.desc()),
        ).label("rn")
        subq = (
            select(Follow.follower_id, Follow.followed_id, rn)
            .where(Follow.followed_id.in_(user_ids))
            .subquery()
        )
        result = await self.session.execute(
            select(subq.c.followed_id, User)
            .join(User, User.id == subq.c.follower_id)
            .where(subq.c.rn <= FOLLOW_LIST_LIMIT)
            .order_by(subq.c.followed_id, subq.c.rn)
        )

        followers_map: Dict[int, List[User]] = defaultdict(list)
        for followed_id, user in result:
            followers_map[followed_id].append(user)

        return [followers_map.get(user_id, []) for user_id in user_ids]


class FollowingLoader(DataLoader):
    """批次載入追蹤中列表的 DataLoader（每個用戶最多 FOLLOW_LIST_LIMIT 個）"""

    def __init__(self, session: AsyncSession):
        super().__init__(load_fn=self.batch_load_following)
        self.session = session

    async def batch_load_following(self, user_ids: List[int]) -> List[List[User]]:
        """批次載入多個用戶追蹤中的用戶，用 window function 在 SQL 端對每個用戶套用上限"""
        from sqlalchemy import func

        rn = func.row_number().over(
            partition_by=Follow.follower_id,
            order_by=(Follow.created_at.desc(), Follow.id.desc()),
        ).label("rn")
        subq = (
            select(Follow.follower_id, Follow.followed_id, rn)
            .where(Follow.follower_id.in_(user_ids))
            .subquery()
        )
        result = await self.session.execute(
            select(subq.c.follower_id, User)
            .join(User, User.id == subq.c.followed_id)
            .where(subq.c.rn <= FOLLOW_LIST_LIMIT)
            .order_by(subq.c.follower_id, subq.c.rn)
        )

        following_map: Dict[int, List[User]] = defaultdict(list)
        for follower_id, user in result:
            following_map[follower_id].append(user)

        return [following_map.get(user_id, []) for user_id in user_ids]


class IsFollowedByUserLoader(DataLoader):
    """批次載入當前用戶是否追蹤某些用戶的 DataLoader"""

    def __init__(self, session: AsyncSession, user_id: Optional[int]):
        super().__init__(load_fn=self.batch_load_is_followed)
        self.session = session
        self.user_id = user_id

    async def batch_load_is_followed(self, user_ids: List[int]) -> List[bool]:
        """批次檢查當前用戶是否追蹤了多個用戶"""
        if not self.user_id:
            return [False] * len(user_ids)

        result = await self.session.execute(
            select(Follow.followed_id)
            .where(Follow.follower_id == self.user_id)
            .where(Follow.followed_id.in_(user_ids))
        )
        followed_ids = set(result.scalars().all())

        return [user_id in followed_ids for user_id in user_ids]


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
        self.comment_count_loader = CommentCountLoader(session)
        self.post_tags_loader = PostTagsLoader(session)
        self.like_count_loader = LikeCountLoader(session)
        self.user_liked_posts_loader = UserLikedPostsLoader(session, user_id)
        self.followers_count_loader = FollowersCountLoader(session)
        self.following_count_loader = FollowingCountLoader(session)
        self.followers_loader = FollowersLoader(session)
        self.following_loader = FollowingLoader(session)
        self.is_followed_loader = IsFollowedByUserLoader(session, user_id)

    def get_user_loader(self) -> UserLoader:
        return self.user_loader

    def get_post_loader(self) -> PostLoader:
        return self.post_loader

    def get_comment_loader(self) -> CommentLoader:
        return self.comment_loader

    def get_post_comments_loader(self) -> PostCommentsLoader:
        return self.post_comments_loader

    def get_comment_count_loader(self) -> CommentCountLoader:
        return self.comment_count_loader

    def get_post_tags_loader(self) -> PostTagsLoader:
        return self.post_tags_loader

    def get_like_count_loader(self) -> LikeCountLoader:
        return self.like_count_loader

    def get_user_liked_posts_loader(self) -> UserLikedPostsLoader:
        return self.user_liked_posts_loader

    def get_followers_count_loader(self) -> FollowersCountLoader:
        return self.followers_count_loader

    def get_following_count_loader(self) -> FollowingCountLoader:
        return self.following_count_loader

    def get_followers_loader(self) -> FollowersLoader:
        return self.followers_loader

    def get_following_loader(self) -> FollowingLoader:
        return self.following_loader

    def get_is_followed_loader(self) -> IsFollowedByUserLoader:
        return self.is_followed_loader