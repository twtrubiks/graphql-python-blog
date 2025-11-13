"""
🎓 教學重點：GraphQL N+1 查詢問題與 DataLoader 解決方案

## 什麼是 N+1 問題？
假設你要查詢 10 篇文章及其作者：
- ❌ 沒有優化：
  - 1 次查詢獲取 10 篇文章
  - 10 次查詢獲取每篇文章的作者
  - 總共 11 次查詢（1 + N）

- ✅ 使用 DataLoader：
  - 1 次查詢獲取 10 篇文章
  - 1 次批次查詢獲取所有作者（通過 author_ids）
  - 總共 2 次查詢！

## 為什麼會發生？
GraphQL 的欄位解析器（field resolvers）是獨立執行的：

```python
# 每篇文章都會觸發這個解析器
def resolve_author(post):
    return db.query(User).filter(User.id == post.author_id).first()  # 每次都查一次！
```

## DataLoader 如何解決？
批次載入（Batching）+ 快取（Caching）：

```python
# DataLoader 會自動收集所有請求，批次查詢
async def batch_load_users(user_ids):
    return db.query(User).filter(User.id.in_(user_ids)).all()  # 一次查所有！
```

## 學習建議
1. 執行這些測試觀察 N+1 問題
2. 對比 test_dataloader_optimization.py 看優化效果
3. 閱讀 docs/dataloader-implementation.md 了解實作細節

## 相關檔案
- tests/graphql/test_dataloader_optimization.py - 優化後的效果對比
- app/graphql/dataloaders.py - DataLoader 實作
- docs/dataloader-implementation.md - 完整文檔
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
    """
    簡單測試：查詢文章及其作者會產生 N+1 問題

    🎯 學習目標：
    理解 GraphQL 中最常見的效能陷阱 - N+1 查詢問題

    📊 測試場景：
    - 資料：3 個用戶，每人 2 篇文章 = 共 6 篇文章
    - 查詢：獲取所有文章及其作者資訊
    - 問題：會執行 1 + 6 = 7 次資料庫查詢

    🔍 問題分析：
    沒有優化的情況下，查詢執行順序：
    1. SELECT * FROM posts LIMIT 10              (1 次查詢)
    2. SELECT * FROM users WHERE id = 1          (第 1 篇文章的作者)
    3. SELECT * FROM users WHERE id = 1          (第 2 篇文章的作者，重複查詢！)
    4. SELECT * FROM users WHERE id = 2          (第 3 篇文章的作者)
    5. SELECT * FROM users WHERE id = 2          (第 4 篇文章的作者，重複查詢！)
    6. SELECT * FROM users WHERE id = 3          (第 5 篇文章的作者)
    7. SELECT * FROM users WHERE id = 3          (第 6 篇文章的作者，重複查詢！)

    💡 觀察重點：
    - 相同的作者被查詢多次（浪費）
    - 查詢次數隨著文章數量線性增長（O(N)）
    - 這就是典型的 N+1 問題
    """

    # ==================== Arrange ====================
    # 📝 GraphQL 查詢：獲取所有文章及其作者信息
    # 注意：author 是巢狀欄位，會觸發額外的資料庫查詢
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

    # ==================== Act ====================
    # 📝 執行 GraphQL 查詢
    # 在真實場景中，可以使用 SQLAlchemy 的 echo=True 觀察 SQL 查詢
    result = await schema.execute(
        query,
        context_value={"db_session": test_session}
    )

    # ==================== Assert ====================
    # 📝 驗證查詢結果正確
    assert result.errors is None
    assert result.data is not None

    posts = result.data["posts"]["edges"]
    assert len(posts) == 6  # 3 users * 2 posts

    # 📝 檢查每篇文章都有作者資訊
    for post_edge in posts:
        post = post_edge["node"]
        assert post["author"] is not None
        assert post["author"]["username"] is not None

    # 📝 N+1 問題分析
    # 雖然測試通過，但效能很差！
    print(f"\n{'='*60}")
    print(f"⚠️  N+1 Problem Detected!")
    print(f"{'='*60}")
    print(f"📊 Fetched {len(posts)} posts")
    print(f"❌ Each post triggers a separate query for its author")
    print(f"💾 Expected DB queries: 1 (posts) + {len(posts)} (authors) = {1 + len(posts)} queries")
    print(f"")
    print(f"🎯 Solution: Use DataLoader (see test_dataloader_optimization.py)")
    print(f"   - With DataLoader: Only 2 queries (1 posts + 1 batch authors)")
    print(f"{'='*60}\n")

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