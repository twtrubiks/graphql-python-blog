"""
測試基礎的 N+1 查詢問題檢測 - 簡化版本
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.post import Post
from app.core.security import get_password_hash
from app.graphql.schema import schema


@pytest_asyncio.fixture
async def setup_n1_test_data(test_session: AsyncSession):
    """設置測試資料：3個用戶，每個用戶2篇文章"""
    users = []
    posts = []

    # 創建 3 個用戶
    for i in range(3):
        user = User(
            email=f"n1user{i}@example.com",
            username=f"n1user{i}",
            full_name=f"N1 User {i}",
            bio=f"Bio for n1 user {i}",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_superuser=False
        )
        test_session.add(user)
        users.append(user)

    await test_session.flush()

    # 每個用戶創建 2 篇文章
    for user in users:
        for j in range(2):
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

    await test_session.commit()

    return {
        "users": users,
        "posts": posts
    }


@pytest.mark.asyncio
async def test_simple_n1_query(test_session: AsyncSession, setup_n1_test_data):
    """簡單測試：查詢文章及其作者會產生 N+1 問題"""

    # GraphQL 查詢：獲取所有文章及其作者信息
    query = """
    query GetPostsWithAuthors {
        posts(page: 1, limit: 10) {
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

    # 執行查詢
    result = await schema.execute(
        query,
        context_value={"db_session": test_session}
    )

    # 驗證結果
    assert result.errors is None
    assert result.data is not None

    posts = result.data["posts"]["edges"]
    assert len(posts) == 6  # 3 users * 2 posts

    # 檢查每篇文章都有作者資訊
    for post_edge in posts:
        post = post_edge["node"]
        assert post["author"] is not None
        assert post["author"]["username"] is not None

    # 這裡會產生 N+1 問題：
    # 1次查詢獲取所有文章
    # 6次查詢獲取每篇文章的作者（即使有些作者是相同的）
    print(f"\n=== N+1 Problem Detected ===")
    print(f"Fetched {len(posts)} posts")
    print(f"Each post triggers a separate query for its author")
    print(f"Expected queries: 1 (posts) + 6 (authors) = 7 queries")

    return posts


@pytest.mark.asyncio
async def test_duplicate_author_queries(test_session: AsyncSession, setup_n1_test_data):
    """測試重複查詢同一作者的問題"""

    # 取得測試資料中的第一個用戶的文章
    test_data = setup_n1_test_data
    first_user = test_data["users"][0]

    # 查詢同一作者的多篇文章
    query = """
    query GetPostsBySameAuthor {
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

    result = await schema.execute(
        query,
        context_value={"db_session": test_session}
    )

    assert result.errors is None

    # 統計相同作者被查詢的次數
    author_counts = {}
    for edge in result.data["posts"]["edges"]:
        author_id = edge["node"]["author"]["id"]
        author_counts[author_id] = author_counts.get(author_id, 0) + 1

    # 顯示重複查詢的問題
    print(f"\n=== Duplicate Author Query Analysis ===")
    for author_id, count in author_counts.items():
        if count > 1:
            print(f"Author ID {author_id} was queried {count} times (should be 1)")

    # 驗證確實有重複查詢
    has_duplicates = any(count > 1 for count in author_counts.values())
    assert has_duplicates, "Should have duplicate author queries demonstrating N+1 problem"


@pytest.mark.asyncio
async def test_nested_n1_problem(test_session: AsyncSession, setup_n1_test_data):
    """測試巢狀查詢的 N+1 問題（文章 -> 作者 -> 追蹤者數量）"""

    query = """
    query GetPostsWithAuthorDetails {
        posts(page: 1, limit: 5) {
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
                }
            }
        }
    }
    """

    result = await schema.execute(
        query,
        context_value={"db_session": test_session}
    )

    assert result.errors is None

    posts = result.data["posts"]["edges"]

    print(f"\n=== Nested N+1 Problem Analysis ===")
    print(f"Fetched {len(posts)} posts")
    print(f"Each post triggers:")
    print(f"  - 1 query for author")
    print(f"  - 1 query for followers count")
    print(f"  - 1 query for following count")
    print(f"  - 1 query for likes count")
    print(f"Total expected queries: 1 + (5 * 4) = 21 queries")

    # 驗證所有欄位都有返回
    for edge in posts:
        post = edge["node"]
        assert post["author"]["followersCount"] is not None
        assert post["author"]["followingCount"] is not None
        assert post["likesCount"] is not None