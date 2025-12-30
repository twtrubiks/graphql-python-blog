# GraphQL Union Types 完整指南

## 📚 目錄

1. [什麼是 Union Types？](#什麼是-union-types)
2. [為什麼需要 Union Types？](#為什麼需要-union-types)
3. [Union Types vs Interface](#union-types-vs-interface)
4. [實作範例：搜尋功能](#實作範例搜尋功能)
5. [最佳實踐](#最佳實踐)
6. [常見問題](#常見問題)

---

## 什麼是 Union Types？

Union Types 是 GraphQL 中的一個強大特性，允許一個欄位返回多種不同類型的物件。

它表示「這個欄位可能返回 A 類型或 B 類型或 C 類型...」的概念。

### 基本語法

```graphql
# Schema 定義
union SearchResult = Post | User | Comment

# 查詢時使用 inline fragments
query {
  search(term: "GraphQL") {
    ... on Post {
      title
      content
    }
    ... on User {
      username
      email
    }
    ... on Comment {
      content
      author
    }
  }
}
```

## 為什麼需要 Union Types？

### 1. 統一介面
單一 API 端點可以返回不同類型的資料，減少端點數量。

**傳統方式（多個端點）：**
```graphql
# 需要維護三個不同的查詢
query SearchPosts($term: String!) {
  searchPosts(term: $term) {
    title
    content
  }
}

query SearchUsers($term: String!) {
  searchUsers(term: $term) {
    username
    email
  }
}

query SearchComments($term: String!) {
  searchComments(term: $term) {
    content
    author
  }
}
```

**使用 Union Types（單一端點）：**
```graphql
# 一個查詢搞定所有類型
query UniversalSearch($term: String!) {
  search(term: $term) {
    ... on Post { title, content }
    ... on User { username, email }
    ... on Comment { content, author }
  }
}
```

### 2. 靈活性
搜尋結果可以包含文章、用戶、標籤等多種類型，不需要分開查詢。

**實際例子：**
```javascript
// ❌ 傳統方式：需要決定搜尋哪種類型
if (searchType === 'posts') {
  results = await searchPosts(keyword);
} else if (searchType === 'users') {
  results = await searchUsers(keyword);
}

// ✅ Union Types：自動返回所有相關類型
const results = await search(keyword);
// 結果可能包含：[Post, User, Comment, ...]
```

### 3. 類型安全
客戶端必須明確處理每種可能的類型，避免運行時錯誤。

**TypeScript 範例：**
```typescript
// 編譯時期就能檢查類型
interface SearchResult {
  __typename: 'Post' | 'User' | 'Comment';
}

function displayResult(item: SearchResult) {
  switch(item.__typename) {
    case 'Post':
      // TypeScript 確保這裡只能存取 Post 的欄位
      return `文章：${item.title}`;
    case 'User':
      // TypeScript 確保這裡只能存取 User 的欄位
      return `用戶：${item.username}`;
    case 'Comment':
      // TypeScript 確保這裡只能存取 Comment 的欄位
      return `評論：${item.content}`;
    default:
      // TypeScript 會警告有未處理的類型
      throw new Error(`未知類型：${item.__typename}`);
  }
}
```

### 4. 效能優化
一次查詢獲取多種類型的資料，減少網路請求。

**效能比較：**
```javascript
// ❌ 多次網路請求（較慢）
const posts = await fetch('/api/searchPosts?q=GraphQL');     // 請求 1：100ms
const users = await fetch('/api/searchUsers?q=GraphQL');     // 請求 2：100ms
const comments = await fetch('/api/searchComments?q=GraphQL'); // 請求 3：100ms
// 總時間：300ms（串列）或 100ms（並行）+ 多次連線開銷

// ✅ 單次網路請求（較快）
const results = await graphql`
  query {
    search(term: "GraphQL") {
      ... on Post { title }
      ... on User { username }
      ... on Comment { content }
    }
  }
`;
// 總時間：100ms + 單次連線開銷
```

### 5. 減少過度獲取（Over-fetching）
只獲取每種類型需要的欄位，避免浪費頻寬。

```graphql
search(term: "GraphQL") {
  ... on Post {
    # 文章需要標題和內容
    title
    content
    publishedAt
  }
  ... on User {
    # 用戶只需要基本資訊
    username
    avatar
  }
  ... on Comment {
    # 評論只需要簡短內容
    content
    createdAt
  }
}
```

### 6. 簡化前端邏輯
前端不需要協調多個 API 呼叫的結果。

```javascript
// ❌ 複雜的前端邏輯
async function getSearchResults(keyword) {
  const [posts, users, comments] = await Promise.all([
    searchPosts(keyword),
    searchUsers(keyword),
    searchComments(keyword)
  ]);

  // 需要手動合併和排序
  const combined = [
    ...posts.map(p => ({...p, type: 'post'})),
    ...users.map(u => ({...u, type: 'user'})),
    ...comments.map(c => ({...c, type: 'comment'}))
  ];

  return combined.sort((a, b) => b.relevance - a.relevance);
}

// ✅ 簡單的前端邏輯
async function getSearchResults(keyword) {
  const { search } = await graphqlQuery(SEARCH_QUERY, { keyword });
  return search; // 後端已經處理好合併和排序
}
```

## Union Types vs Interface

### Union Types
- **使用場景**：類型之間沒有共同欄位
- **定義方式**：`union Result = TypeA | TypeB`
- **查詢方式**：必須使用 inline fragments
- **例子**：搜尋結果、時間軸活動

### Interface
- **使用場景**：類型之間有共同欄位
- **定義方式**：定義共享欄位，類型實作介面
- **查詢方式**：可直接查詢共同欄位
- **例子**：Node 介面（都有 id）、媒體內容（都有 url）

### 比較表格

| 特性 | Union Types | Interface |
|------|------------|-----------|
| 共同欄位 | 不需要 | 必須有 |
| 類型關係 | 完全獨立 | 有繼承關係 |
| 查詢複雜度 | 較高（需 inline fragments） | 較低（可查詢共同欄位） |
| 使用場景 | 異質資料集合 | 同質資料變體 |

## 實作範例：搜尋功能

### 🎨 實際應用場景

在這個部落格專案中，Union Types 主要應用於以下場景：

#### 1. 全站搜尋功能

搜尋可能返回文章或用戶：

```python
SearchResult = Union[PostType, UserType]
```

**使用情境：**

- 搜尋 "Python" 可能找到：
  - 標題含 "Python" 的文章
  - 用戶名含 "Python" 的用戶
  - 內容提到 "Python" 的文章

#### 2. 活動時間線（未來功能）

顯示不同類型的活動：

```python
TimelineActivity = Union[PostPublishedActivity, CommentAddedActivity, UserFollowedActivity]
```

**使用情境：**

- 發表文章活動
- 新增評論活動
- 追蹤用戶活動

### 1. 定義 Union Type (Python/Strawberry)

```python
# app/graphql/types/search.py
import strawberry
from typing import Union, Annotated

from app.graphql.types.post import PostType
from app.graphql.types.user import UserType

# 定義 Union Type - 搜尋結果可以是文章或用戶
SearchResult = Annotated[
    Union[PostType, UserType],
    strawberry.union("SearchResult")
]
```

### 2. 實作 Resolver

```python
# app/graphql/queries/search.py
import strawberry
from typing import List
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user import User
from app.graphql.types.search import SearchResult
from app.graphql.types.post import PostType
from app.graphql.types.user import UserType


@strawberry.type
class SearchQuery:
    @strawberry.field
    async def search(
        self,
        term: str,
        info: strawberry.Info
    ) -> List[SearchResult]:
        """搜尋文章和用戶"""
        db: AsyncSession = info.context["db_session"]
        results: List[SearchResult] = []

        search_term = term.lower()

        # 搜尋文章（只搜尋已發布的）
        post_stmt = select(Post).where(
            or_(
                func.lower(Post.title).contains(search_term),
                func.lower(Post.content).contains(search_term),
                func.lower(Post.excerpt).contains(search_term)
            ),
            Post.status == "published"
        )

        post_result = await db.execute(post_stmt)
        posts = post_result.scalars().all()

        for post in posts:
            # 轉換為 PostType
            post_type = PostType(
                id=post.id,
                title=post.title,
                slug=post.slug,
                content=post.content,
                status=post.status,
                author_id=post.author_id,
                published_at=post.published_at,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
            # 設置私有的 excerpt 欄位
            post_type._excerpt = post.excerpt
            results.append(post_type)

        # 搜尋用戶
        user_stmt = select(User).where(
            or_(
                func.lower(User.username).contains(search_term),
                func.lower(User.bio).contains(search_term) if User.bio else False
            )
        )

        user_result = await db.execute(user_stmt)
        users = user_result.scalars().all()

        for user in users:
            # 轉換為 UserType
            user_type = UserType(
                id=str(user.id),
                email=user.email,
                username=user.username,
                bio=user.bio,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=user.created_at
            )
            results.append(user_type)

        return results
```

### 3. 客戶端查詢

```graphql
query SearchContent($term: String!) {
  search(term: $term) {
    __typename  # 用於識別返回的類型
    ... on PostType {
      postId: id
      title
      excerpt
      author {
        username
      }
    }
    ... on UserType {
      userId: id
      username
      bio
      followersCount
    }
  }
}
```

### 4. 客戶端使用說明

#### GraphQL 查詢解析

- **`__typename`**: 每個 Union Type 結果都包含此欄位，用於識別實際類型
- **`... on TypeName`**: Inline Fragment 語法，根據類型選擇性查詢欄位
- **別名（Alias）**: 如 `postId: id`，避免不同類型間的欄位名稱衝突

#### 客戶端處理流程

1. **發送查詢**: 使用 GraphQL 客戶端（如 Houdini）發送包含 inline fragments 的查詢
2. **接收結果**: 獲得包含不同類型物件的陣列
3. **類型判斷**: 根據 `__typename` 欄位判斷每個結果的實際類型
4. **條件渲染**: 根據不同類型顯示不同的 UI 元件

### 5. 處理查詢結果 (JavaScript/TypeScript)

```typescript
interface SearchResult {
  __typename: 'PostType' | 'UserType';
}

interface PostResult extends SearchResult {
  __typename: 'PostType';
  postId: string;
  title: string;
  excerpt: string;
  author: {
    username: string;
  };
}

interface UserResult extends SearchResult {
  __typename: 'UserType';
  userId: string;
  username: string;
  bio?: string;
  followersCount: number;
}

// 處理搜尋結果
function handleSearchResults(results: SearchResult[]) {
  results.forEach(result => {
    switch (result.__typename) {
      case 'PostType':
        const post = result as PostResult;
        console.log(`文章: ${post.title}`);
        break;

      case 'UserType':
        const user = result as UserResult;
        console.log(`用戶: ${user.username}`);
        break;

      default:
        console.warn('未知類型:', result);
    }
  });
}
```

## 最佳實踐

### 1. 命名規範

- Union Type 名稱應該描述性強：`SearchResult`、`TimelineItem`
- 使用 Type 後綴區分：`PostType`、`UserType`

### 2. 欄位衝突處理

當不同類型有相同名稱但不同類型的欄位時，使用別名：

```graphql
query {
  search(term: "test") {
    ... on PostType {
      postId: id  # Int!
      title
    }
    ... on UserType {
      userId: id  # ID!
      username
    }
  }
}
```

### 3. 類型判斷

始終使用 `__typename` 來判斷返回的具體類型：

```graphql
query {
  search(term: "test") {
    __typename  # 返回 "PostType" 或 "UserType"
    ... on PostType {
      title
    }
    ... on UserType {
      username
    }
  }
}
```

### 4. 錯誤處理

考慮添加錯誤類型到 Union：

```python
SearchResult = Annotated[
    Union[PostType, UserType, ErrorType],
    strawberry.union("SearchResult")
]
```

### 5. 文檔化

為 Union Type 和每個可能的類型提供清晰的文檔：

```python
@strawberry.type
class SearchQuery:
    @strawberry.field
    async def search(
        self,
        term: str,
        info: strawberry.Info
    ) -> List[SearchResult]:
        """
        搜尋文章和用戶

        返回 SearchResult Union Type，可能包含：
        - PostType: 符合搜尋條件的文章
        - UserType: 符合搜尋條件的用戶

        Args:
            term: 搜尋關鍵字（不區分大小寫）

        Returns:
            混合的文章和用戶結果列表
        """
        # ... 實作
```

## 常見問題

### Q1: Union Type 可以包含標量類型嗎？

**A**: 不行，Union Type 只能包含物件類型（Object Types），不能包含標量類型（Scalar Types）如 String、Int。

### Q2: Union Type 可以嵌套嗎？

**A**: 不能直接嵌套，但可以在 Union Type 的成員類型中使用其他 Union Type。

### Q3: 如何處理空結果？

**A**: 返回空陣列 `[]` 而不是 `null`，這樣客戶端處理更簡單。

### Q4: Union Type vs 多個查詢端點？

**A**: Union Type 優點：

- 減少網路請求
- 統一的搜尋介面
- 更好的快取策略

多個端點優點：

- 更簡單的客戶端邏輯
- 可以針對性優化
- 更細粒度的權限控制

### Q5: 如何測試 Union Type？

**A**: 測試每種可能的返回類型：

```python
# 測試返回 PostType
async def test_search_returns_posts():
    result = await search("Python")
    assert any(r.__typename == "PostType" for r in result)

# 測試返回 UserType
async def test_search_returns_users():
    result = await search("developer")
    assert any(r.__typename == "UserType" for r in result)

# 測試混合結果
async def test_search_returns_mixed():
    result = await search("GraphQL")
    types = {r.__typename for r in result}
    assert "PostType" in types
    assert "UserType" in types
```

## 進階應用

### 1. 時間軸/動態流

```graphql
union TimelineItem =
  | PostCreated
  | CommentAdded
  | UserFollowed
  | PostLiked

query GetTimeline {
  timeline {
    ... on PostCreated {
      post { title }
      createdAt
    }
    ... on CommentAdded {
      comment { content }
      post { title }
    }
    ... on UserFollowed {
      follower { username }
      following { username }
    }
    ... on PostLiked {
      user { username }
      post { title }
    }
  }
}
```

### 2. 通知系統

```graphql
union Notification =
  | NewFollower
  | PostComment
  | PostLike
  | Mention

query GetNotifications {
  notifications {
    ... on NewFollower {
      follower { username, avatar }
      timestamp
    }
    ... on PostComment {
      comment { content }
      post { title }
      author { username }
    }
    # ... 其他類型
  }
}
```

### 3. 錯誤處理

```graphql
union CreatePostResult =
  | PostType
  | ValidationError
  | PermissionError

mutation CreatePost($input: PostInput!) {
  createPost(input: $input) {
    ... on PostType {
      id
      title
      slug
    }
    ... on ValidationError {
      field
      message
    }
    ... on PermissionError {
      message
      requiredPermission
    }
  }
}
```

## 總結

Union Types 是 GraphQL 中處理多型返回值的強大工具。它們特別適合：

1. **搜尋功能** - 返回不同類型的搜尋結果
2. **活動流** - 顯示不同類型的用戶活動
3. **通知系統** - 處理各種通知類型
4. **錯誤處理** - 區分成功結果和各種錯誤

正確使用 Union Types 可以讓你的 GraphQL API 更靈活、更強大，同時保持類型安全。

## 相關資源

- [GraphQL 官方文檔 - Union Types](https://graphql.org/learn/schema/#union-types)
- [Strawberry GraphQL - Union Types](https://strawberry.rocks/docs/types/union)
- [本專案實作](./tasks.md#53-graphql-進階特性精選-tdd)
- [架構設計文檔](./architecture.md#graphql-層)