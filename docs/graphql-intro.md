# GraphQL 與 GraphiQL 使用指南

## 什麼是 GraphiQL？

GraphiQL 是 GraphQL 的官方互動式 IDE（整合開發環境），提供在瀏覽器中探索和測試 GraphQL API 的功能。

### 訪問方式
- **開發環境**：http://localhost:8000/graphql
- **功能**：只在 DEBUG 模式下開啟（生產環境會關閉）

### GraphiQL 介面說明

```
┌─────────────────────────────────────────────────────┐
│  GraphiQL                                    Docs ▼ │
├──────────────────┬──────────────────────────────────┤
│                  │                                  │
│  查詢編輯器       │        執行結果                   │
│                  │                                  │
│  {               │  {                               │
│    hello         │    "data": {                     │
│  }               │      "hello": "Hello World!"     │
│                  │    }                             │
│                  │  }                               │
│                  │                                  │
├──────────────────┴──────────────────────────────────┤
│  Query Variables (變數區)                           │
└─────────────────────────────────────────────────────┘
```

### 主要功能
- **語法高亮**：自動顯示語法顏色
- **自動完成**：按 Ctrl+Space 顯示可用欄位
- **錯誤提示**：即時顯示語法錯誤
- **文檔瀏覽**：點擊右上角 "Docs" 查看 API 文檔
- **歷史記錄**：保存執行過的查詢

---

## GraphQL 查詢語法

### 基本概念

GraphQL 不是 JSON！它是一種專門設計的查詢語言，用於精確描述你需要的資料。

### GraphQL vs JSON 對比

| 特性 | GraphQL 查詢 | JSON |
|------|-------------|------|
| 語法 | `hello` | `"hello": null` |
| 參數 | `user(id: 1)` | 不支援函數調用 |
| 欄位名 | 不需要引號 | 必須用引號 |
| 分隔符 | 換行或空格 | 逗號 `,` |
| 冒號 | 只用於參數 | 用於鍵值對 |

---

## 查詢語法範例

### 1. 簡單查詢

最基本的查詢，直接請求欄位：

```graphql
{
  hello
  version
}
```

**回應**：
```json
{
  "data": {
    "hello": "Hello World!",
    "version": "1.0.0"
  }
}
```

### 2. 帶參數查詢

傳遞參數給欄位：

```graphql
{
  hello(name: "Alice")
}
```

**回應**：
```json
{
  "data": {
    "hello": "Hello Alice!"
  }
}
```

### 3. 多個查詢組合

同時請求多個欄位和參數：

```graphql
{
  greeting1: hello(name: "Alice")
  greeting2: hello(name: "Bob")
  version
}
```

**回應**：
```json
{
  "data": {
    "greeting1": "Hello Alice!",
    "greeting2": "Hello Bob!",
    "version": "1.0.0"
  }
}
```

### 4. 嵌套查詢（未來實作）

查詢關聯資料：

```graphql
{
  user(id: 1) {
    username
    email
    posts {
      title
      content
      createdAt
    }
  }
}
```

### 5. 使用變數

將動態值從查詢中分離：

**查詢**：
```graphql
query GetGreeting($userName: String) {
  hello(name: $userName)
}
```

**變數**（在 Query Variables 區域）：
```json
{
  "userName": "Charlie"
}
```

---

## Mutation（突變）語法

用於修改資料的操作：

### 基本 Mutation

```graphql
mutation {
  echo(message: "Test message")
}
```

**回應**：
```json
{
  "data": {
    "echo": "Echo: Test message"
  }
}
```

### 帶變數的 Mutation（未來實作）

```graphql
mutation CreateUser($email: String!, $password: String!) {
  register(email: $email, password: $password) {
    user {
      id
      email
    }
    token
  }
}
```

---

## 實用技巧

### 1. 快捷鍵
- **Ctrl + Space**：自動完成
- **Ctrl + Enter**：執行查詢
- **Shift + Ctrl + P**：美化查詢

### 2. 探索 Schema
1. 點擊右上角 "Docs"
2. 瀏覽可用的 Query 和 Mutation
3. 查看每個欄位的類型和說明

### 3. 除錯技巧
- 從簡單查詢開始，逐步增加複雜度
- 使用別名避免欄位名衝突
- 善用變數讓查詢更靈活

### 4. 查詢片段（Fragment）- 進階功能

重複使用查詢結構：

```graphql
fragment UserInfo on User {
  id
  username
  email
}

query {
  user(id: 1) {
    ...UserInfo
    posts {
      title
    }
  }
}
```

---

## 常見錯誤

### 1. 語法錯誤
❌ 錯誤：使用 JSON 語法
```graphql
{
  "hello": "World"
}
```

✅ 正確：GraphQL 語法
```graphql
{
  hello(name: "World")
}
```

### 2. 缺少必要參數
❌ 錯誤：遺漏必要參數
```graphql
{
  user  # 需要 id 參數
}
```

✅ 正確：提供必要參數
```graphql
{
  user(id: 1)
}
```

### 3. 欄位不存在
❌ 錯誤：請求不存在的欄位
```graphql
{
  helloWorld  # 應該是 hello
}
```

✅ 正確：使用正確的欄位名
```graphql
{
  hello
}
```

---

## 最佳實踐

1. **命名查詢**：給複雜查詢加上描述性名稱
2. **使用變數**：避免在查詢中硬編碼值
3. **請求需要的資料**：只請求實際使用的欄位
4. **錯誤處理**：檢查回應中的 errors 欄位
5. **分頁處理**：大量資料使用分頁參數

---

## 進階主題

### Subscription（訂閱）- 即時更新

> 詳細實作與限制說明請參考 [Subscription 即時通訊指南](./subscription-guide.md)

```graphql
subscription OnCommentAdded($postId: ID!) {
  commentAdded(postId: $postId) {
    id
    content
    author {
      username
    }
  }
}
```

### Directive（指令）
```graphql
query GetUser($includeEmail: Boolean!) {
  user(id: 1) {
    username
    email @include(if: $includeEmail)
  }
}
```

---

## 總結

GraphiQL 是開發 GraphQL API 的強大工具，透過其直覺的介面和豐富的功能，可以：

1. 快速測試和驗證 API
2. 探索可用的查詢和突變
3. 生成文檔和範例
4. 除錯和優化查詢

記住：GraphQL 查詢語言不是 JSON，而是專門設計來描述客戶端需要的資料結構的語言。

---

## 參考資源

- [GraphQL 官方文檔](https://graphql.org/learn/)
- [GraphiQL GitHub](https://github.com/graphql/graphiql)
- [Strawberry GraphQL 文檔](https://strawberry.rocks/)