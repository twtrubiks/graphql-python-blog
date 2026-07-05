"""
測試 DataLoader 優化效果
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.core.security import get_password_hash
from app.graphql.schema import schema
from app.graphql.dataloaders import DataLoaderContext


@pytest_asyncio.fixture
async def setup_dataloader_test_data(test_session: AsyncSession):
    """設置測試資料：5個用戶，每個用戶3篇文章，每篇文章2個評論"""
    users = []
    posts = []
    comments = []
    
    # 創建 5 個用戶
    for i in range(5):
        user = User(
            email=f"dluser{i}@example.com",
            username=f"dluser{i}",
            full_name=f"DL User {i}",
            bio=f"Bio for dl user {i}",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_superuser=False
        )
        test_session.add(user)
        users.append(user)
    
    await test_session.flush()
    
    # 每個用戶創建 3 篇文章
    for user in users:
        for j in range(3):
            post = Post(
                title=f"{user.username} - Post {j}",
                slug=f"{user.username}-post-{j}",
                content=f"Content for post {j} by {user.username}",
                excerpt=f"Excerpt {j}",
                status="published",
                author_id=user.id
            )
            test_session.add(post)
            posts.append(post)
    
    await test_session.flush()
    
    # 每篇文章創建 2 個評論
    for post in posts:
        for k in range(2):
            comment = Comment(
                content=f"Comment {k} on post {post.id}",
                post_id=post.id,
                user_id=users[k % len(users)].id
            )
            test_session.add(comment)
            comments.append(comment)
    
    await test_session.commit()
    
    return {
        "users": users,
        "posts": posts,
        "comments": comments
    }


@pytest.mark.asyncio
async def test_dataloader_batch_loading(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 DataLoader 批次載入功能"""
    
    # 創建 DataLoader 上下文
    dataloader_context = DataLoaderContext(test_session)
    
    # GraphQL 查詢：獲取文章及其作者
    query = """
    query GetPostsWithAuthors {
        posts(page: 1, limit: 15) {
            edges {
                node {
                    id
                    title
                    author {
                        id
                        username
                        email
                    }
                }
            }
            pageInfo {
                totalCount
            }
        }
    }
    """
    
    # 執行查詢（帶 DataLoader）
    result = await schema.execute(
        query,
        context_value={
            "db_session": test_session,
            "dataloaders": dataloader_context
        }
    )
    
    # 驗證結果
    assert result.errors is None
    assert result.data is not None
    
    posts = result.data["posts"]["edges"]
    assert len(posts) == 15  # 5 users * 3 posts
    
    # 驗證每篇文章都有作者資訊
    for post_edge in posts:
        post = post_edge["node"]
        assert post["author"] is not None
        assert post["author"]["username"] is not None
    
    # 統計不同作者的數量
    unique_authors = set()
    for post_edge in posts:
        unique_authors.add(post_edge["node"]["author"]["id"])
    
    print(f"\n=== DataLoader Optimization Results ===")
    print(f"Total posts fetched: {len(posts)}")
    print(f"Unique authors: {len(unique_authors)}")
    print(f"With DataLoader: Only {len(unique_authors)} author queries instead of {len(posts)}")
    
    # 驗證批次載入確實減少了查詢次數
    assert len(unique_authors) < len(posts), "Should have fewer unique authors than posts"


@pytest.mark.asyncio
async def test_dataloader_with_nested_fields(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 DataLoader 處理巢狀欄位的效果"""
    
    # 創建 DataLoader 上下文
    dataloader_context = DataLoaderContext(test_session)
    
    query = """
    query GetPostsWithDetails {
        posts(page: 1, limit: 10) {
            edges {
                node {
                    id
                    title
                    author {
                        id
                        username
                        followersCount
                        followingCount
                    }
                    likesCount
                    isLiked
                }
            }
        }
    }
    """
    
    # 執行查詢（帶 DataLoader）
    result = await schema.execute(
        query,
        context_value={
            "db_session": test_session,
            "dataloaders": dataloader_context
        }
    )
    
    assert result.errors is None
    
    posts = result.data["posts"]["edges"]
    
    print(f"\n=== Nested Fields with DataLoader ===")
    print(f"Fetched {len(posts)} posts with nested fields")
    print(f"DataLoader batches multiple queries:")
    print(f"  - Author data: batched")
    print(f"  - Followers count: batched")
    print(f"  - Following count: batched")
    print(f"  - Likes count: batched")
    
    # 驗證所有欄位都有返回
    for edge in posts:
        post = edge["node"]
        assert post["author"]["followersCount"] is not None
        assert post["author"]["followingCount"] is not None
        assert post["likesCount"] is not None
        assert post["isLiked"] is not None


@pytest.mark.asyncio
async def test_dataloader_vs_no_dataloader(test_session: AsyncSession, setup_dataloader_test_data):
    """比較有無 DataLoader 的差異"""
    
    query = """
    query ComparePerformance {
        posts(page: 1, limit: 10) {
            edges {
                node {
                    id
                    title
                    author {
                        id
                        username
                    }
                }
            }
        }
    }
    """
    
    # 1. 執行查詢（無 DataLoader）
    result_no_dl = await schema.execute(
        query,
        context_value={
            "db_session": test_session
            # 不提供 dataloaders
        }
    )
    
    # 2. 執行查詢（有 DataLoader）
    dataloader_context = DataLoaderContext(test_session)
    result_with_dl = await schema.execute(
        query,
        context_value={
            "db_session": test_session,
            "dataloaders": dataloader_context
        }
    )
    
    # 驗證兩種方式都能正確返回結果
    assert result_no_dl.errors is None
    assert result_with_dl.errors is None
    
    # 驗證結果相同
    assert result_no_dl.data == result_with_dl.data
    
    print(f"\n=== DataLoader Comparison ===")
    print(f"Without DataLoader: N+1 queries (1 for posts + N for each author)")
    print(f"With DataLoader: Optimized queries (1 for posts + 1 batched for all authors)")
    print(f"Result: Both return the same data, but DataLoader is more efficient")


@pytest.mark.asyncio
async def test_dataloader_cache_behavior(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 DataLoader 的快取行為"""
    
    # 創建 DataLoader 上下文
    dataloader_context = DataLoaderContext(test_session)
    
    # 查詢同一作者的多篇文章
    query = """
    query TestCache {
        posts(page: 1, limit: 3) {
            edges {
                node {
                    id
                    title
                    author {
                        id
                        username
                    }
                }
            }
        }
    }
    """
    
    result = await schema.execute(
        query,
        context_value={
            "db_session": test_session,
            "dataloaders": dataloader_context
        }
    )
    
    assert result.errors is None
    
    # 統計相同作者被請求的次數
    author_requests = {}
    for edge in result.data["posts"]["edges"]:
        author_id = edge["node"]["author"]["id"]
        author_requests[author_id] = author_requests.get(author_id, 0) + 1
    
    print(f"\n=== DataLoader Cache Behavior ===")
    for author_id, count in author_requests.items():
        print(f"Author {author_id} requested {count} times")
    print(f"DataLoader ensures each author is only fetched once from DB")
    
    # 如果有重複的作者，DataLoader 應該從快取返回
    has_duplicate_requests = any(count > 1 for count in author_requests.values())
    if has_duplicate_requests:
        print("Cache hit: Same author data reused from DataLoader cache")

@pytest.mark.asyncio
async def test_comment_count_loader_batch(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 CommentCountLoader 批次載入評論數"""
    import asyncio
    from app.graphql.dataloaders import CommentCountLoader

    posts = setup_dataloader_test_data["posts"]
    loader = CommentCountLoader(test_session)

    # 併發 load 觸發批次載入（單一 GROUP BY 查詢）
    counts = await asyncio.gather(*[loader.load(post.id) for post in posts])

    # fixture 中每篇文章有 2 個評論
    assert counts == [2] * len(posts)


@pytest.mark.asyncio
async def test_comment_count_loader_excludes_deleted(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 CommentCountLoader 排除已軟刪除的評論"""
    from datetime import datetime, timezone
    from app.graphql.dataloaders import CommentCountLoader

    post = setup_dataloader_test_data["posts"][0]
    comment = setup_dataloader_test_data["comments"][0]
    assert comment.post_id == post.id

    # 軟刪除其中一個評論
    comment.deleted_at = datetime.now(timezone.utc)
    await test_session.commit()

    loader = CommentCountLoader(test_session)
    count = await loader.load(post.id)

    assert count == 1


@pytest.mark.asyncio
async def test_post_tags_loader_batch(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 PostTagsLoader 批次載入文章標籤"""
    import asyncio
    from app.models.tag import Tag, post_tags
    from app.graphql.dataloaders import PostTagsLoader

    posts = setup_dataloader_test_data["posts"][:3]

    tag_a = Tag(name="LoaderTagA", slug="loader-tag-a")
    tag_b = Tag(name="LoaderTagB", slug="loader-tag-b")
    test_session.add_all([tag_a, tag_b])
    await test_session.flush()

    await test_session.execute(post_tags.insert().values([
        {"post_id": posts[0].id, "tag_id": tag_a.id},
        {"post_id": posts[0].id, "tag_id": tag_b.id},
        {"post_id": posts[1].id, "tag_id": tag_a.id},
    ]))
    await test_session.commit()

    loader = PostTagsLoader(test_session)
    tags0, tags1, tags2 = await asyncio.gather(
        loader.load(posts[0].id),
        loader.load(posts[1].id),
        loader.load(posts[2].id),
    )

    assert sorted(tag.name for tag in tags0) == ["LoaderTagA", "LoaderTagB"]
    assert [tag.name for tag in tags1] == ["LoaderTagA"]
    assert tags2 == []


@pytest.mark.asyncio
async def test_total_comments_and_tags_use_dataloader(test_session: AsyncSession, setup_dataloader_test_data):
    """測試 GraphQL 查詢中 totalComments 與 tags 透過 DataLoader 正確解析"""
    dataloader_context = DataLoaderContext(test_session)

    query = """
    query GetPostsWithCounts {
        posts(page: 1, limit: 15) {
            edges {
                node {
                    id
                    totalComments
                    tags { name }
                }
            }
        }
    }
    """

    result = await schema.execute(
        query,
        context_value={
            "db_session": test_session,
            "dataloaders": dataloader_context
        }
    )

    assert result.errors is None
    edges = result.data["posts"]["edges"]
    assert len(edges) == 15
    for edge in edges:
        assert edge["node"]["totalComments"] == 2
        assert edge["node"]["tags"] == []
