# GraphQL Fragment 完整指南

## 📚 目錄

1. [什麼是 Fragment？](#什麼是-fragment)
2. [為什麼需要 Fragment？](#為什麼需要-fragment)
3. [Fragment 基本語法](#fragment-基本語法)
4. [實作範例](#實作範例)
5. [進階用法](#進階用法)
6. [最佳實踐](#最佳實踐)
7. [常見問題](#常見問題)

---

## 什麼是 Fragment？

Fragment 是 GraphQL 中用於**重用查詢片段**的機制。它允許你定義一組欄位，然後在多個查詢、變更或訂閱中重複使用這些欄位。

可以把 Fragment 想像成：
- **程式設計中的函數**：定義一次，多處呼叫
- **CSS 中的 class**：定義樣式規則，套用到多個元素
- **模板引擎中的 partial**：可重用的模板片段

### 核心概念

```graphql
# 定義 Fragment
fragment FragmentName on TypeName {
  field1
  field2
  field3
}

# 使用 Fragment
query {
  someField {
    ...FragmentName
  }
}
```

## 為什麼需要 Fragment？

### 1. 減少重複程式碼

**沒有 Fragment 的情況：**
```graphql
query GetUserAndPosts {
  me {
    id
    username
    email
    bio
    avatarUrl
    createdAt
  }

  posts {
    author {
      id
      username
      email
      bio
      avatarUrl
      createdAt
    }
  }

  topUsers {
    id
    username
    email
    bio
    avatarUrl
    createdAt
  }
}
```

**使用 Fragment 優化：**
```graphql
fragment UserInfo on UserType {
  id
  username
  email
  bio
  avatarUrl
  createdAt
}

query GetUserAndPosts {
  me {
    ...UserInfo
  }

  posts {
    author {
      ...UserInfo
    }
  }

  topUsers {
    ...UserInfo
  }
}
```

### 2. 提升維護性

當需要新增欄位時，只需修改 Fragment 定義：

```graphql
fragment UserInfo on UserType {
  id
  username
  email
  bio
  avatarUrl
  createdAt
  followersCount  # 新增欄位
  isVerified      # 新增欄位
}
```

所有使用這個 Fragment 的地方都會自動包含新欄位。

### 3. 型別安全

Fragment 綁定特定類型，確保欄位存在：

```graphql
# ✅ 正確：PostType 有 title 欄位
fragment PostInfo on PostType {
  title
  content
}

# ❌ 錯誤：UserType 沒有 title 欄位
fragment UserInfo on UserType {
  title  # 會報錯
}
```

### 4. 提高可讀性

Fragment 名稱可以表達語義，讓查詢更易理解：

```graphql
fragment BasicUserInfo on UserType {
  id
  username
  avatarUrl
}

fragment DetailedUserInfo on UserType {
  ...BasicUserInfo
  email
  bio
  createdAt
  followersCount
}

fragment UserWithPosts on UserType {
  ...DetailedUserInfo
  posts {
    ...PostSummary
  }
}
```

## Fragment 基本語法

### 定義 Fragment

```graphql
fragment FragmentName on TypeName {
  field1
  field2
  nestedObject {
    nestedField1
    nestedField2
  }
}
```

### 使用 Fragment

使用展開運算符（`...`）來引用 Fragment：

```graphql
query GetUser {
  user(id: "123") {
    ...FragmentName
  }
}
```

### Fragment 中使用變數

Fragment 可以使用查詢中定義的變數：

```graphql
fragment PostsWithPagination on UserType {
  posts(limit: $limit, offset: $offset) {
    id
    title
    createdAt
  }
}

query GetUserPosts($userId: ID!, $limit: Int, $offset: Int) {
  user(id: $userId) {
    ...PostsWithPagination
  }
}
```

## 實作範例

### 範例 1：部落格文章查詢

```graphql
# 定義基本資訊 Fragment
fragment AuthorBasic on UserType {
  id
  username
  avatarUrl
}

fragment PostBasic on PostType {
  id
  title
  slug
  excerpt
  createdAt
}

# 定義詳細資訊 Fragment
fragment PostDetailed on PostType {
  ...PostBasic
  content
  updatedAt
  author {
    ...AuthorBasic
  }
  tags {
    id
    name
  }
}

# 使用 Fragment 的查詢
query GetBlogPosts($limit: Int = 10) {
  posts(limit: $limit) {
    edges {
      node {
        ...PostDetailed
      }
    }
  }

  featuredPost {
    ...PostDetailed
  }
}
```

### 範例 2：巢狀 Fragment

```graphql
fragment CommentInfo on Comment {
  id
  content
  createdAt
  author {
    ...AuthorBasic  # 重用上面定義的 Fragment
  }
}

fragment PostWithComments on PostType {
  ...PostDetailed    # 重用文章詳細資訊
  comments(limit: 5) {
    ...CommentInfo   # 評論資訊
  }
  commentsCount
}

query GetPostWithDiscussion($postId: ID!) {
  post(id: $postId) {
    ...PostWithComments
  }
}
```

### 範例 3：條件式 Fragment

使用內聯 Fragment 處理不同類型：

```graphql
fragment SearchResult on SearchResultUnion {
  __typename
  ... on PostType {
    id
    title
    excerpt
    author {
      ...AuthorBasic
    }
  }
  ... on UserType {
    id
    username
    bio
    followersCount
  }
}

query Search($term: String!) {
  search(term: $term) {
    ...SearchResult
  }
}
```

## 進階用法

### 1. Fragment 組合

建立 Fragment 層次結構：

```graphql
# 基礎層
fragment UserId on UserType {
  id
}

# 簡要層
fragment UserSummary on UserType {
  ...UserId
  username
  avatarUrl
}

# 詳細層
fragment UserProfile on UserType {
  ...UserSummary
  email
  bio
  createdAt
}

# 完整層
fragment UserComplete on UserType {
  ...UserProfile
  posts {
    ...PostBasic
  }
  followers {
    ...UserSummary
  }
  following {
    ...UserSummary
  }
}
```

### 2. Fragment 與 Interface

Fragment 可以定義在 Interface 上：

```graphql
interface Node {
  id: ID!
}

fragment NodeId on Node {
  id
}

# 可以用在任何實作 Node 的類型
query {
  user(id: "1") {
    ...NodeId
  }
  post(id: "2") {
    ...NodeId
  }
}
```

### 3. Fragment 與 Union Types

處理 Union Types 的 Fragment：

```graphql
fragment TimelineItem on TimelineUnion {
  __typename
  ... on PostCreated {
    post {
      ...PostBasic
    }
    createdAt
  }
  ... on CommentAdded {
    comment {
      ...CommentInfo
    }
    post {
      ...PostBasic
    }
  }
  ... on UserFollowed {
    follower {
      ...UserSummary
    }
    following {
      ...UserSummary
    }
  }
}
```

## 最佳實踐

### 1. 命名規範

- **描述性命名**：使用清晰、描述性的名稱
  - ✅ `UserProfileInfo`
  - ❌ `Data1`

- **層次命名**：反映資料的詳細程度
  - `UserBasic`：基本資訊
  - `UserDetailed`：詳細資訊
  - `UserComplete`：完整資訊

### 2. 組織結構

```javascript
// fragments/user.js
export const USER_BASIC = `
  fragment UserBasic on UserType {
    id
    username
    avatarUrl
  }
`;

export const USER_DETAILED = `
  ${USER_BASIC}
  fragment UserDetailed on UserType {
    ...UserBasic
    email
    bio
    createdAt
  }
`;

// fragments/post.js
import { USER_BASIC } from './user';

export const POST_WITH_AUTHOR = `
  ${USER_BASIC}
  fragment PostWithAuthor on PostType {
    id
    title
    author {
      ...UserBasic
    }
  }
`;
```

### 3. 避免過度巢狀

```graphql
# ❌ 過度巢狀
fragment A on Type {
  ...B
}
fragment B on Type {
  ...C
}
fragment C on Type {
  ...D
}
fragment D on Type {
  field
}

# ✅ 適度組合
fragment UserCore on UserType {
  id
  username
}

fragment UserProfile on UserType {
  ...UserCore
  email
  bio
}
```

### 4. 效能考量

- **避免過度獲取**：只包含需要的欄位
- **注意深度**：避免過深的巢狀查詢
- **重用粒度**：在重用性和特定性之間找平衡

### 5. 版本管理

當 API 演進時：

```graphql
# v1 - 原始版本
fragment UserInfoV1 on UserType {
  id
  username
  email
}

# v2 - 新增欄位
fragment UserInfoV2 on UserType {
  id
  username
  email
  isVerified  # 新欄位
  role        # 新欄位
}

# 漸進式遷移
query GetUser {
  user {
    ...UserInfoV1  # 舊客戶端
    # ...UserInfoV2  # 新客戶端
  }
}
```

## Fragment vs Function 對比

| Fragment | Function |
|----------|----------|
| 定義查詢結構 | 定義邏輯處理 |
| 編譯時展開 | 運行時執行 |
| 無參數（但可用變數） | 可傳參數 |
| 只能在同類型使用 | 可用於任何地方 |
| 減少查詢字串大小 | 減少程式碼重複 |

## 簡單總結

Fragment 就是：

1. **查詢的「函數」** - 定義一次，多處調用

2. **DRY 原則實踐** - Don't Repeat Yourself

3. **組件化思維** - 每個 UI 組件對應一個 Fragment

4. **維護友善** - 改一處，全部同步

把 Fragment 想成是「打包好的查詢欄位組合」，需要時就用 `...FragmentName` 展開，就像調用函數一樣簡單！

## 常見問題

### Q1: Fragment 是在客戶端還是伺服器端處理？

**A**: Fragment 主要是客戶端功能，但處理流程如下：
1. 客戶端定義和組合 Fragment
2. 發送查詢時，Fragment 隨查詢一起發送
3. 伺服器端解析並展開 Fragment
4. 返回請求的資料

### Q2: Fragment 可以遞迴引用嗎？

**A**: 不行，Fragment 不能直接或間接引用自己，這會造成無限遞迴：

```graphql
# ❌ 錯誤：遞迴引用
fragment UserWithFriends on UserType {
  id
  username
  friends {
    ...UserWithFriends  # 遞迴！
  }
}
```

解決方案：使用有限深度的 Fragment：

```graphql
# ✅ 正確：有限深度
fragment UserBasic on UserType {
  id
  username
}

fragment UserWithFriends on UserType {
  ...UserBasic
  friends {
    ...UserBasic  # 不遞迴
  }
}
```

### Q3: Fragment 可以有參數嗎？

**A**: Fragment 本身不能有參數，但可以使用查詢變數：

```graphql
# Fragment 使用查詢變數
fragment PostsPage on UserType {
  posts(limit: $limit, offset: $offset) {
    id
    title
  }
}

query GetUserPosts($userId: ID!, $limit: Int, $offset: Int) {
  user(id: $userId) {
    ...PostsPage
  }
}
```

### Q4: Fragment 與 DataLoader 如何配合？

**A**: Fragment 不影響 DataLoader 的運作。DataLoader 在解析欄位時批次處理，無論欄位是否來自 Fragment：

```graphql
fragment PostWithAuthor on PostType {
  id
  title
  author {  # DataLoader 會批次載入
    id
    username
  }
}

query GetPosts {
  posts {
    ...PostWithAuthor  # 多個文章的作者會批次載入
  }
}
```

### Q5: 如何在不同檔案間共享 Fragment？

**A**: 使用模組系統：

```javascript
// fragments/user.graphql
fragment UserBasic on UserType {
  id
  username
}

// queries/posts.graphql
#import "./fragments/user.graphql"

query GetPosts {
  posts {
    author {
      ...UserBasic
    }
  }
}
```

或使用 JavaScript/TypeScript：

```typescript
// fragments/user.ts
export const USER_BASIC = gql`
  fragment UserBasic on UserType {
    id
    username
  }
`;

// queries/posts.ts
import { USER_BASIC } from '../fragments/user';

export const GET_POSTS = gql`
  ${USER_BASIC}
  query GetPosts {
    posts {
      author {
        ...UserBasic
      }
    }
  }
`;
```

## 實際測試範例

我們的專案包含完整的 Fragment 測試，驗證了以下功能：

1. **Fragment 在多個查詢中重用** ([test_fragment_in_multiple_queries](../backend/tests/graphql/test_fragment_reuse.py))
2. **巢狀 Fragment** ([test_nested_fragments](../backend/tests/graphql/test_fragment_reuse.py))
3. **型別安全性** ([test_fragment_type_safety](../backend/tests/graphql/test_fragment_reuse.py))
4. **減少重複程式碼** ([test_fragment_reduces_duplication](../backend/tests/graphql/test_fragment_reuse.py))
5. **與變數配合使用** ([test_fragment_with_variables](../backend/tests/graphql/test_fragment_reuse.py))

## 總結

Fragment 是 GraphQL 中提升程式碼品質的重要工具：

**減少重複**：定義一次，多處使用

**提升維護性**：集中管理欄位定義

**型別安全**：編譯時期檢查

**增強可讀性**：語義化的命名

**組合彈性**：可巢狀和組合使用

正確使用 Fragment 可以讓你的 GraphQL 查詢更加優雅、易維護和高效。

## 本專案 Fragment 實作

本專案前端使用 Houdini GraphQL 客戶端，已實作以下 Fragments：

### Fragment 文件結構

```
frontend/src/lib/graphql/fragments/
├── AuthorBasic.gql      # 作者基本資訊（id, username, avatarUrl）
├── AuthorDetailed.gql   # 作者詳細資訊（含 bio, followersCount 等）
├── TagInfo.gql          # 標籤資訊（id, name, slug）
├── PageInfoFields.gql   # 分頁資訊（Relay Connection Pattern）
├── PostCard.gql         # 文章卡片（列表頁用）
└── CommentInfo.gql      # 評論資訊
```

### 使用範例

```graphql
# GetPosts.gql - 使用 Fragment 簡化查詢
query GetPosts($page: Int = 1, $limit: Int = 10, $search: String) {
  posts(page: $page, limit: $limit, search: $search) {
    edges {
      node {
        ...PostCard @mask_disable
      }
    }
    pageInfo {
      ...PageInfoFields @mask_disable
    }
  }
}
```

### Houdini Fragment Masking

Houdini 預設啟用 **Fragment Masking**，這是一種安全機制：

- **啟用 Masking**：組件只能訪問自己聲明的 Fragment 字段
- **禁用 Masking**：可以直接訪問所有字段

本專案使用 `@mask_disable` 指令禁用 masking，讓數據可以直接訪問：

```graphql
# 使用 @mask_disable 讓 Fragment 內的字段可直接訪問
query GetPost($slug: String) {
  post(slug: $slug) {
    author {
      ...AuthorDetailed @mask_disable
    }
  }
}
```

> **注意**：生產環境中大型團隊協作時，建議啟用 Masking 以獲得更好的類型安全和組件隔離。

## 相關資源

- [GraphQL 官方文檔 - Fragments](https://graphql.org/learn/queries/#fragments)
- [Houdini Fragment 文檔](https://houdinigraphql.com/api/fragment)
- [本專案測試範例](../backend/tests/graphql/test_fragment_reuse.py)
- [Union Types 指南](./union-types-guide.md)
- [架構設計文檔](./architecture.md)