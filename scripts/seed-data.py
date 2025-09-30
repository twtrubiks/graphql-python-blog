#!/usr/bin/env python3

"""
測試資料生成腳本

這個腳本會生成測試用的資料，包括：
- 用戶帳號
- 文章內容
- 評論
- 按讚記錄
- 追蹤關係

使用方式：
    python3 ../scripts/seed-data.py
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import List
from pathlib import Path

# 將 backend 目錄加入 Python 路徑
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.models.post import Post, PostStatus
from app.models.comment import Comment
from app.models.like import Like
from app.models.follow import Follow
from app.models.tag import Tag
from app.core.security import get_password_hash
from sqlalchemy import select


# 測試資料
USERS_DATA = [
    {
        "email": "admin@example.com",
        "username": "admin",
        "password": "admin123",
        "full_name": "系統管理員",
        "bio": "我是系統管理員，負責維護這個部落格平台",
        "is_superuser": True
    },
    {
        "email": "alice@example.com",
        "username": "alice",
        "password": "alice123",
        "full_name": "Alice Chen",
        "bio": "熱愛程式設計的軟體工程師，專注於後端開發和系統架構"
    },
    {
        "email": "bob@example.com",
        "username": "bob",
        "password": "bob123",
        "full_name": "Bob Lee",
        "bio": "前端工程師，喜歡研究新技術和使用者體驗設計"
    },
    {
        "email": "carol@example.com",
        "username": "carol",
        "password": "carol123",
        "full_name": "Carol Wang",
        "bio": "全端工程師，GraphQL 愛好者"
    },
    {
        "email": "david@example.com",
        "username": "david",
        "password": "david123",
        "full_name": "David Liu",
        "bio": "DevOps 工程師，專注於 CI/CD 和雲端架構"
    }
]

TAGS_DATA = [
    "GraphQL", "Python", "FastAPI", "Svelte", "TypeScript",
    "Docker", "PostgreSQL", "WebSocket", "Tutorial", "Backend",
    "Frontend", "Database", "API", "Performance", "Security"
]

POSTS_DATA = [
    {
        "title": "深入理解 GraphQL DataLoader",
        "content": """# GraphQL DataLoader 完整指南

DataLoader 是解決 GraphQL N+1 查詢問題的利器。本文將深入探討其原理和實作。

## 什麼是 N+1 問題？

當我們查詢多個資源及其關聯資料時，很容易產生 N+1 次資料庫查詢：

```graphql
query {
  posts {
    id
    title
    author {
      name
    }
  }
}
```

## DataLoader 如何解決？

DataLoader 透過批次處理和快取機制，將多次查詢合併為一次：

1. **收集階段**：收集所有查詢需求
2. **批次執行**：一次性查詢所有資料
3. **分發結果**：按照原始順序返回結果

## 實作範例

```python
class UserLoader(DataLoader):
    async def batch_load_fn(self, user_ids):
        users = await User.filter(id__in=user_ids)
        user_map = {user.id: user for user in users}
        return [user_map.get(user_id) for user_id in user_ids]
```

這樣就能將 N+1 次查詢優化為 2 次！""",
        "excerpt": "了解如何使用 DataLoader 優化 GraphQL 查詢效能",
        "tags": ["GraphQL", "Performance", "Backend"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "Svelte 5 Runes 系統詳解",
        "content": """# Svelte 5 的革命性改變：Runes

Svelte 5 引入了 Runes，徹底改變了響應式狀態管理的方式。

## 核心 Runes

### $state
創建響應式狀態：
```javascript
let count = $state(0);
```

### $derived
計算衍生狀態：
```javascript
let doubled = $derived(count * 2);
```

### $effect
響應式副作用：
```javascript
$effect(() => {
    console.log('Count changed:', count);
});
```

## 為什麼選擇 Runes？

1. 更好的 TypeScript 支援
2. 更直觀的心智模型
3. 更細粒度的響應式控制
4. 與現有生態系統更好的整合""",
        "excerpt": "探索 Svelte 5 的新響應式系統",
        "tags": ["Svelte", "Frontend", "Tutorial"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "使用 FastAPI + Strawberry 構建 GraphQL API",
        "content": """# FastAPI + Strawberry：Python GraphQL 的最佳組合

## 為什麼選擇這個技術棧？

- **FastAPI**：現代化、高效能的 Python Web 框架
- **Strawberry**：Python 的 GraphQL 函式庫，支援類型提示
- **異步支援**：原生支援 async/await

## 快速開始

```python
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: str = "World") -> str:
        return f"Hello {name}!"

schema = strawberry.Schema(query=Query)
app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/graphql")
```

就這麼簡單！""",
        "excerpt": "學習如何使用 Python 構建現代化的 GraphQL API",
        "tags": ["GraphQL", "Python", "FastAPI", "Tutorial"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "WebSocket 實現即時通訊",
        "content": """# GraphQL Subscription 與 WebSocket

即時通訊是現代應用的重要功能，GraphQL Subscription 提供了優雅的解決方案。

## 實作步驟

1. 設置 WebSocket 連線
2. 定義 Subscription Type
3. 實作事件推送機制
4. 前端訂閱處理

## 程式碼範例

後端：
```python
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def comment_added(self, post_id: int) -> Comment:
        # 訂閱邏輯
        pass
```

前端：
```javascript
subscription OnCommentAdded($postId: ID!) {
    commentAdded(postId: $postId) {
        id
        content
        author {
            username
        }
    }
}
```""",
        "excerpt": "實作 GraphQL Subscription 實現即時更新",
        "tags": ["GraphQL", "WebSocket", "Tutorial"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "Docker Compose 開發環境設置",
        "content": """# 使用 Docker Compose 統一開發環境

## 為什麼需要 Docker？

- 環境一致性
- 簡化部署
- 團隊協作
- 服務編排

## 完整配置

```yaml
version: '3.8'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: blog

  backend:
    build: ./backend
    depends_on:
      - db

  frontend:
    build: ./frontend
    depends_on:
      - backend
```

一個命令啟動所有服務！""",
        "excerpt": "一鍵搭建完整的開發環境",
        "tags": ["Docker", "DevOps", "Tutorial"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "PostgreSQL 效能優化技巧",
        "content": """# PostgreSQL 查詢優化實戰

資料庫效能是應用效能的關鍵。本文分享實用的優化技巧。

## 索引策略

1. B-tree 索引：最常用的索引類型
2. GIN 索引：全文搜尋
3. 部分索引：針對特定條件

## 查詢優化

- 使用 EXPLAIN ANALYZE
- 避免 N+1 查詢
- 適當使用 JOIN
- 連線池管理

## 實戰案例

優化前：
```sql
SELECT * FROM posts WHERE status = 'published' ORDER BY created_at DESC;
```

優化後：
```sql
CREATE INDEX idx_posts_status_created ON posts(status, created_at DESC);
```

效能提升 10 倍！""",
        "excerpt": "掌握 PostgreSQL 效能優化的關鍵技巧",
        "tags": ["PostgreSQL", "Database", "Performance"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "JWT 認證最佳實踐",
        "content": """# JWT 認證系統設計

安全的認證系統是應用的基石。

## JWT 結構

- Header：演算法資訊
- Payload：用戶資料
- Signature：簽名驗證

## 安全考量

1. 使用 HTTPS
2. 設置合理的過期時間
3. Refresh Token 機制
4. 黑名單管理

## 實作建議

- Access Token：15 分鐘
- Refresh Token：7 天
- 使用 RS256 演算法
- 避免儲存敏感資訊""",
        "excerpt": "構建安全可靠的 JWT 認證系統",
        "tags": ["Security", "API", "Backend"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "TypeScript 進階型別系統",
        "content": """# TypeScript 進階技巧

TypeScript 的型別系統非常強大，掌握進階技巧能大幅提升程式碼品質。

## 進階型別

### 條件型別
```typescript
type IsString<T> = T extends string ? true : false;
```

### 映射型別
```typescript
type Readonly<T> = {
    readonly [P in keyof T]: T[P];
}
```

### 模板字面量型別
```typescript
type EventName<T> = `on${Capitalize<T>}`;
```

這些技巧讓程式碼更安全、更易維護！""",
        "excerpt": "探索 TypeScript 的進階型別特性",
        "tags": ["TypeScript", "Frontend", "Tutorial"],
        "status": PostStatus.PUBLISHED
    },
    {
        "title": "GraphQL Fragment 重用技巧",
        "content": """# GraphQL Fragment：減少重複的利器

Fragment 是 GraphQL 中重用查詢片段的機制。

## 基本用法

```graphql
fragment UserInfo on User {
    id
    username
    avatarUrl
}

query GetPosts {
    posts {
        author {
            ...UserInfo
        }
    }
}
```

## 進階技巧

1. 嵌套 Fragment
2. 內聯 Fragment
3. 介面和聯合型別

Fragment 讓查詢更清晰、更易維護！""",
        "excerpt": "使用 Fragment 優化 GraphQL 查詢",
        "tags": ["GraphQL", "API", "Tutorial"],
        "status": PostStatus.DRAFT
    },
    {
        "title": "測試驅動開發實踐",
        "content": """# TDD：測試驅動開發

TDD 是一種開發方法論，先寫測試再寫程式碼。

## 紅綠重構循環

1. 紅：寫一個失敗的測試
2. 綠：寫最少的程式碼讓測試通過
3. 重構：改善程式碼品質

## 實戰範例

```python
def test_user_creation():
    user = User(email='test@example.com')
    assert user.email == 'test@example.com'
```

TDD 能顯著提升程式碼品質和信心！""",
        "excerpt": "實踐 TDD 提升程式碼品質",
        "tags": ["Testing", "Tutorial", "Backend"],
        "status": PostStatus.DRAFT
    }
]

COMMENTS_DATA = [
    "很棒的文章，學到了很多！",
    "感謝分享，解決了我的問題。",
    "可以再詳細說明一下這個部分嗎？",
    "程式碼範例很實用，已經應用在專案中了。",
    "期待看到更多相關的內容！",
    "這個方法真的很有效，效能提升明顯。",
    "有沒有相關的開源專案推薦？",
    "文章寫得很清楚，適合初學者。",
    "建議補充一些錯誤處理的範例。",
    "這是我看過最好的教學文章之一！"
]


async def create_users(session: AsyncSession) -> List[User]:
    """創建測試用戶"""
    users = []
    for user_data in USERS_DATA:
        # 檢查用戶是否已存在
        existing = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing_user = existing.scalar_one_or_none()
        if existing_user:
            print(f"用戶 {user_data['email']} 已存在，使用現有用戶")
            users.append(existing_user)
            continue

        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=user_data.get("full_name"),
            bio=user_data.get("bio"),
            is_superuser=user_data.get("is_superuser", False),
            is_active=True
        )
        session.add(user)
        users.append(user)

    await session.commit()
    print(f"✅ 創建了 {len([u for u in users if u.id is None])} 個新用戶，共 {len(users)} 個用戶")
    return users


async def create_tags(session: AsyncSession) -> List[Tag]:
    """創建標籤"""
    tags = []
    for tag_name in TAGS_DATA:
        # 檢查標籤是否已存在
        existing = await session.execute(
            select(Tag).where(Tag.name == tag_name)
        )
        existing_tag = existing.scalar_one_or_none()
        if existing_tag:
            tags.append(existing_tag)
            continue

        tag = Tag(
            name=tag_name,
            slug=tag_name.lower().replace(" ", "-")
        )
        session.add(tag)
        tags.append(tag)

    await session.commit()
    print(f"✅ 創建了 {len([t for t in tags if t.id is None])} 個新標籤，共 {len(tags)} 個標籤")
    return tags


async def create_posts(session: AsyncSession, users: List[User], tags: List[Tag]) -> List[Post]:
    """創建文章"""
    posts = []
    created_count = 0
    skipped_count = 0

    if not users:
        print("⚠️ 沒有可用的用戶，跳過文章創建")
        return posts

    for post_data in POSTS_DATA:
        # 生成 slug
        base_slug = post_data["title"].lower().replace(" ", "-")

        # 檢查文章是否已存在（根據 slug）
        existing = await session.execute(
            select(Post).where(Post.slug == base_slug)
        )
        existing_post = existing.scalar_one_or_none()

        if existing_post:
            print(f"文章 '{post_data['title']}' 已存在，跳過")
            posts.append(existing_post)
            skipped_count += 1
            continue

        # 隨機選擇作者
        author = random.choice(users)

        # 創建文章
        post = Post(
            title=post_data["title"],
            slug=base_slug,
            content=post_data["content"],
            excerpt=post_data["excerpt"],
            author_id=author.id,
            status=post_data["status"],
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
            published_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)) if post_data["status"] == PostStatus.PUBLISHED else None
        )

        # 添加標籤
        post_tags = random.sample(tags, k=min(len(post_data["tags"]), len(tags)))
        post.tags.extend(post_tags)

        session.add(post)
        posts.append(post)
        created_count += 1

    await session.commit()
    print(f"✅ 創建了 {created_count} 篇新文章，跳過了 {skipped_count} 篇已存在的文章，共 {len(posts)} 篇文章")
    return posts


async def create_comments(session: AsyncSession, posts: List[Post], users: List[User]):
    """創建評論"""
    comment_count = 0

    if not posts or not users:
        print("⚠️ 沒有文章或用戶，跳過評論創建")
        return

    for post in posts:
        # 每篇文章隨機生成 0-5 則評論
        num_comments = random.randint(0, 5)

        for _ in range(num_comments):
            commenter = random.choice(users)
            comment_text = random.choice(COMMENTS_DATA)

            comment = Comment(
                content=comment_text,
                post_id=post.id,
                user_id=commenter.id,
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72))
            )
            session.add(comment)
            comment_count += 1

    await session.commit()
    print(f"✅ 創建了 {comment_count} 則評論")


async def create_likes(session: AsyncSession, posts: List[Post], users: List[User]):
    """創建按讚記錄"""
    like_count = 0
    skipped_count = 0

    if not posts or not users:
        print("⚠️ 沒有文章或用戶，跳過按讚創建")
        return

    for post in posts:
        # 隨機選擇 0-3 個用戶按讚
        likers = random.sample(users, k=random.randint(0, min(3, len(users))))

        for user in likers:
            # 檢查是否已經按過讚
            existing = await session.execute(
                select(Like).where(
                    (Like.user_id == user.id) &
                    (Like.post_id == post.id)
                )
            )
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

            like = Like(
                user_id=user.id,
                post_id=post.id,
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))
            )
            session.add(like)
            like_count += 1

    await session.commit()
    print(f"✅ 創建了 {like_count} 個新按讚，跳過了 {skipped_count} 個已存在的按讚")


async def create_follows(session: AsyncSession, users: List[User]):
    """創建追蹤關係"""
    follow_count = 0
    skipped_count = 0

    if len(users) < 2:
        print("⚠️ 用戶數量不足，跳過追蹤關係創建")
        return

    for user in users:
        # 每個用戶隨機追蹤 0-2 個其他用戶
        potential_follows = [u for u in users if u.id != user.id]
        to_follow = random.sample(potential_follows, k=random.randint(0, min(2, len(potential_follows))))

        for target in to_follow:
            # 檢查是否已經追蹤
            existing = await session.execute(
                select(Follow).where(
                    (Follow.follower_id == user.id) &
                    (Follow.followed_id == target.id)
                )
            )
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

            follow = Follow(
                follower_id=user.id,
                followed_id=target.id,
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
            )
            session.add(follow)
            follow_count += 1

    await session.commit()
    print(f"✅ 創建了 {follow_count} 個新追蹤關係，跳過了 {skipped_count} 個已存在的追蹤關係")


async def main():
    """主函數"""
    print("🚀 開始生成測試資料...")

    # 初始化資料庫
    await init_db()

    # 獲取資料庫連線
    async with AsyncSessionLocal() as session:
        # 創建測試資料
        users = await create_users(session)
        tags = await create_tags(session)
        posts = await create_posts(session, users, tags)
        await create_comments(session, posts, users)
        await create_likes(session, posts, users)
        await create_follows(session, users)

    print("\n✨ 測試資料生成完成！")
    print("\n測試帳號：")
    for user_data in USERS_DATA[:3]:
        print(f"  📧 {user_data['email']} / 🔑 {user_data['password']}")


if __name__ == "__main__":
    asyncio.run(main())