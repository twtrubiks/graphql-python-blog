# GraphQL Blog Frontend

使用 SvelteKit (Svelte 5) + TypeScript + Tailwind CSS + Houdini 建立的現代化部落格前端應用程式。

## 技術堆疊

- **SvelteKit** - 全端框架
- **Svelte 5** - 使用最新的 runes 語法 (`$state`, `$props`, `$effect`, `$derived`)
- **TypeScript** - 類型安全
- **Tailwind CSS** - 實用優先的 CSS 框架
- **Vite** - 快速的建置工具
- **Houdini v2.0.0-next.9** - GraphQL 客戶端（完整支援 Svelte 5）

## 快速開始

### 1. 安裝依賴
```bash
npm install
```

### 2. 啟動後端服務
```bash
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 生成 GraphQL 型別
```bash
npm run codegen
```

### 4. 啟動開發伺服器
```bash
npm run dev
```
應用程式將在 http://localhost:5173 啟動

## Svelte 5 新特性

本專案使用 Svelte 5 的新語法特性：

### Runes
- `$state()` - 響應式狀態管理
- `$props()` - 元件屬性定義
- `$effect()` - 副作用處理
- `$derived()` - 衍生狀態

### Snippets
使用 `{@render children()}` 取代傳統的 slots

### 事件處理
使用 `onclick` 取代 `on:click`

## 專案結構

```
frontend/
├── src/
│   ├── routes/           # SvelteKit 路由
│   │   ├── +layout.svelte    # 根 layout（使用 Svelte 5 語法）
│   │   ├── +layout.ts        # SSR/CSR 配置
│   │   ├── +page.svelte      # 首頁
│   │   ├── +page.ts          # 頁面載入函數
│   │   ├── login/            # 登入頁面
│   │   └── +error.svelte     # 錯誤頁面
│   ├── lib/
│   │   ├── components/   # 可重用元件
│   │   │   └── Button.svelte # Svelte 5 元件範例
│   │   ├── graphql/      # GraphQL 操作定義
│   │   │   ├── queries/      # GraphQL 查詢
│   │   │   │   ├── GetPosts.gql
│   │   │   │   ├── GetPost.gql
│   │   │   │   ├── GetMe.gql
│   │   │   │   └── SearchContent.gql
│   │   │   ├── mutations/    # GraphQL 變更
│   │   │   │   ├── Login.gql
│   │   │   │   ├── Register.gql
│   │   │   │   ├── CreatePost.gql
│   │   │   │   ├── AddComment.gql
│   │   │   │   ├── LikePost.gql
│   │   │   │   └── UnlikePost.gql
│   │   │   └── subscriptions/ # GraphQL 訂閱
│   │   │       ├── CommentAdded.gql
│   │   │       └── UserStatus.gql
│   │   ├── stores/       # Svelte stores
│   │   │   └── auth.svelte.ts # 認證 store（.svelte.ts 支援 runes）
│   │   └── utils/        # 工具函數
│   ├── client.ts        # Houdini GraphQL 客戶端設置
│   ├── env.d.ts         # 環境變數 TypeScript 定義
│   ├── app.html         # HTML 模板
│   ├── app.css          # 全域樣式（Tailwind）
│   └── app.d.ts         # TypeScript 定義
├── .houdini/            # Houdini 生成的檔案（git-ignored）
├── static/              # 靜態檔案
├── .env                 # 環境變數
├── houdini.config.js    # Houdini 配置
├── svelte.config.js     # SvelteKit 配置
├── tailwind.config.js   # Tailwind 配置
├── postcss.config.js    # PostCSS 配置
└── tsconfig.json        # TypeScript 配置
```

## GraphQL 整合 (Houdini)

### 為什麼選擇 Houdini？

#### 🚀 獨特優勢
- **編譯時優化**：所有 GraphQL 操作在構建時處理，運行時零開銷
- **SvelteKit 原生整合**：專為 SvelteKit 設計，完美支援 SSR/CSR/SSG
- **零配置體驗**：開箱即用的快取、分頁、樂觀更新
- **檔案系統路由**：GraphQL 檔案自動與 SvelteKit 路由關聯
- **極小的 Bundle Size**：相比 Apollo Client 減少 70% 的打包體積

#### 📊 與其他方案比較

| 特性 | Houdini | Apollo Client | URQL | 手寫 Fetch |
|------|---------|---------------|------|------------|
| Bundle Size | ~15KB | ~50KB | ~25KB | 0KB |
| TypeScript 支援 | 自動生成* | 需要 codegen** | 需要 codegen** | 手動 |
| SvelteKit 整合 | 原生 | 需要配置 | 部分支援 | 手動 |
| 快取管理 | 自動 | 手動配置 | 手動配置 | 無 |
| SSR 支援 | 完美 | 複雜 | 可用 | 手動 |
| 學習曲線 | 低 | 高 | 中 | 低 |

> **\* Houdini 自動生成**：生成完整的客戶端程式碼（包含類型、快取邏輯、錯誤處理等）

> **\*\* Apollo/URQL codegen**：只生成 TypeScript 類型定義，其他功能需手動實作

#### 💡 開發體驗
- **即時型別生成**：修改 `.gql` 檔案立即獲得 TypeScript 型別
- **Svelte 5 完美配合**：與 runes 系統無縫整合
- **優秀的錯誤提示**：編譯時捕獲 GraphQL 錯誤
- **智慧快取更新**：自動更新相關查詢的快取

### 主要功能
- ✅ 自動 TypeScript 型別生成
- ✅ GraphQL 查詢、變更和訂閱支援
- ✅ JWT 認證整合
- ✅ Svelte 5 語法支援 (runes)
- ✅ 自動快取管理
- ✅ WebSocket 即時訂閱
- ✅ 樂觀更新支援
- ✅ 離線快取持久化

### GraphQL 操作與 .gql 檔案

#### 什麼是 .gql 檔案？
`.gql` 是 GraphQL Query Language 檔案，用來存放 GraphQL 的查詢、變更和訂閱操作。這些檔案讓你可以：
- 將 GraphQL 操作與程式碼分離
- 獲得更好的語法高亮和自動完成
- 重複使用相同的操作
- 更容易追蹤 API 變更

#### 專案檔案結構
```
src/lib/graphql/
├── queries/           # 查詢操作
│   ├── GetPosts.gql      # 獲取文章列表
│   ├── GetPost.gql       # 獲取單篇文章
│   ├── GetMe.gql         # 獲取當前使用者
│   └── SearchContent.gql # 搜尋內容
├── mutations/         # 變更操作
│   ├── Login.gql         # 使用者登入
│   ├── Register.gql      # 使用者註冊
│   ├── CreatePost.gql    # 創建文章
│   ├── AddComment.gql    # 新增評論
│   ├── LikePost.gql      # 按讚文章
│   └── UnlikePost.gql    # 取消按讚
└── subscriptions/     # 訂閱操作
    ├── CommentAdded.gql  # 新評論通知
    └── UserStatus.gql    # 使用者狀態變更
```

#### .gql 檔案範例
```graphql
# GetPosts.gql
query GetPosts($page: Int!, $limit: Int) {
  posts(page: $page, limit: $limit) {
    edges {
      node {
        id
        title
        excerpt
        author { username }
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
```

### Houdini 開發工作流程

#### 1️⃣ 編寫 .gql 檔案
創建或修改 `.gql` 檔案定義你的 GraphQL 操作

#### 2️⃣ 執行程式碼生成
```bash
npm run codegen        # 單次生成
npm run codegen:watch  # 監聽模式（推薦開發時使用）
```

#### 3️⃣ Houdini 自動生成
- **TypeScript 類型**：`GetPostsQuery`, `GetPostsVariables`
- **載入函數**：`load_GetPosts()`
- **Store**：`GetPosts$result`
- **快取管理**：自動處理
- **錯誤狀態**：內建支援

#### 4️⃣ 在 Svelte 中使用
```svelte
<script lang="ts">
  import { load_GetPosts } from '$houdini'

  // 類型都是自動生成的！
  const { data, error, fetching } = await load_GetPosts({
    variables: { page: 1, limit: 10 }
  })
</script>
```

### 在元件中使用查詢 (Svelte 5)

```svelte
<script lang="ts">
  import { graphql } from '$houdini';

  // Svelte 5: 使用 $state rune
  let currentPage = $state(1);

  // 定義 GraphQL 查詢
  const postsQuery = graphql(`
    query GetPosts($page: Int!) {
      posts(page: $page) {
        edges {
          node {
            id
            title
            excerpt
          }
        }
      }
    }
  `);

  // 執行查詢
  $effect(() => {
    postsQuery.fetch({ variables: { page: currentPage }});
  });

  // 使用 $derived 處理資料
  let posts = $derived(postsQuery.data?.posts.edges || []);
</script>
```

### 使用變更 (Mutations)

```svelte
<script lang="ts">
  import { graphql } from '$houdini';
  import { auth } from '$lib/stores/auth.svelte';

  const loginMutation = graphql(`
    mutation Login($email: String!, $password: String!) {
      login(email: $email, password: $password) {
        user { id username email }
        token
      }
    }
  `);

  async function handleLogin(email: string, password: string) {
    const result = await loginMutation.mutate({ email, password });

    if (result.data?.login) {
      await auth.login(result.data.login.user, result.data.login.token);
    }
  }
</script>
```

### 使用訂閱 (Subscriptions)

```svelte
<script lang="ts">
  import { graphql } from '$houdini';

  const commentSubscription = graphql(`
    subscription CommentAdded($postId: ID!) {
      commentAdded(postId: $postId) {
        id
        content
        author { username }
      }
    }
  `);

  // 訂閱會自動處理 WebSocket 連接
  $effect(() => {
    commentSubscription.listen({ postId: '1' });
  });
</script>
```

## 認證處理

認證 token 會自動從 localStorage 讀取並附加到每個請求的 Authorization header 中。

```typescript
// 登入後儲存 token
await auth.login(userData, token);

// 登出時清除 token
await auth.logout();

// 檢查認證狀態
if (auth.isAuthenticated) {
  // 已登入
}
```

## SSR/CSR 配置

預設啟用 SSR（伺服器端渲染）和 CSR（客戶端渲染）。可在 `+page.ts` 或 `+layout.ts` 中調整：

```typescript
export const ssr = true;  // 伺服器端渲染
export const csr = true;  // 客戶端渲染
export const prerender = false;  // 預渲染
```

## 開發指南

### 創建新頁面
在 `src/routes/` 下創建 `+page.svelte` 檔案

### 使用 Svelte 5 元件
```svelte
<script lang="ts">
  let { title, onclick } = $props<{
    title: string;
    onclick?: () => void;
  }>();

  let count = $state(0);
</script>

<button {onclick}>
  {title}: {count}
</button>
```

### 使用 Svelte 5 Store
```typescript
// auth.svelte.ts
let user = $state<User | null>(null);
let isAuthenticated = $derived(user !== null);
```

### 型別生成與 Codegen 詳解

#### 為什麼需要 npm run codegen？

雖然 Houdini 提供「自動生成」，但這個生成過程需要被觸發：

1. **讀取來源**：掃描所有 `.gql` 檔案和內嵌的 GraphQL 查詢
2. **連接後端**：從 GraphQL 後端拉取最新的 schema
3. **生成程式碼**：
   - TypeScript 類型定義
   - 客戶端執行程式碼
   - 快取管理邏輯
   - Store 和 載入函數
4. **輸出檔案**：生成到 `.houdini/` 和 `$houdini/` 目錄

#### Codegen 指令說明

```bash
# 基本生成：讀取 .gql 檔案並生成程式碼
npm run codegen

# 拉取 Schema：從後端更新 schema 並生成
npm run codegen:pull

# 監聽模式：檔案變更時自動重新生成（開發時推薦）
npm run codegen:watch
```

#### 何時需要執行 Codegen？

- ✅ 首次設置專案時
- ✅ 新增或修改 `.gql` 檔案後
- ✅ 後端 GraphQL Schema 更新後
- ✅ 更新 Houdini 版本後

#### Houdini vs 其他工具的 Codegen 差異

| 工具 | Codegen 生成內容 | 還需要手寫的部分 |
|------|-----------------|-----------------|
| **Houdini** | 類型 + 完整客戶端程式碼 | 幾乎不需要 |
| **Apollo** | 只有 TypeScript 類型 | 查詢執行、快取配置、錯誤處理 |
| **URQL** | 只有 TypeScript 類型 | 客戶端設置、快取策略 |
| **手寫** | 無 | 全部都要寫 |

## 可用腳本

- `npm run dev` - 啟動開發伺服器
- `npm run build` - 建置生產版本
- `npm run preview` - 預覽生產版本
- `npm run check` - 類型檢查
- `npm run lint` - ESLint 檢查
- `npm run format` - Prettier 格式化
- `npm run codegen` - 生成 GraphQL 型別
- `npm run codegen:pull` - 從後端拉取 schema
- `npm run codegen:watch` - 監聽 GraphQL 檔案變更

## 疑難排解

### 型別錯誤
如果遇到型別錯誤，請執行：
```bash
npm run codegen
```

### CORS 錯誤
檢查：
1. 後端服務是否正在運行
2. `.env` 中的端點設置是否正確
3. 後端 CORS 設定是否允許前端域名

### 認證問題
確認：
1. Token 是否正確儲存在 localStorage
2. 後端是否正確解析 Authorization header
3. Token 是否已過期

### Import 錯誤 - "$houdini" 模組找不到
如果遇到 `Failed to resolve import "$houdini"` 錯誤：

1. 確認 `vite.config.ts` 包含 Houdini 插件：
```typescript
import houdini from 'houdini/vite';
// ...
plugins: [houdini(), sveltekit()]
```

2. 重新執行 codegen：
```bash
npm run codegen
```

### Process is not defined 錯誤
這通常發生在 `houdini.config.js` 中使用 `process.env`。解決方法：
- 在 `houdini.config.js` 中使用硬編碼的 URL
- 使用 `import.meta.env` 在客戶端代碼中

## 注意事項

- 使用 Svelte 5 最新語法
- TypeScript strict mode 已啟用
- Tailwind CSS 已配置自定義主題色彩
- 路徑別名已設定（$lib, $components, $stores, $utils）
- 環境變數使用 `VITE_` 前綴以在客戶端使用
- Houdini 會自動管理快取，可在 `houdini.config.js` 中自訂策略

## 相關文檔

- [Houdini 官方文檔](https://houdinigraphql.com/)
- [Svelte 5 文檔](https://svelte.dev/)
- [SvelteKit 文檔](https://kit.svelte.dev/)
- [GraphQL 文檔](https://graphql.org/)
- [Tailwind CSS 文檔](https://tailwindcss.com/)