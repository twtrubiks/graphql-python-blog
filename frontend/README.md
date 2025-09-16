# GraphQL Blog Frontend

使用 SvelteKit (Svelte 5) + TypeScript + Tailwind CSS 建立的現代化部落格前端應用程式。

## 技術堆疊

- **SvelteKit** - 全端框架
- **Svelte 5** - 使用最新的 runes 語法 (`$state`, `$props`, `$effect`, `$derived`)
- **TypeScript** - 類型安全
- **Tailwind CSS** - 實用優先的 CSS 框架
- **Vite** - 快速的建置工具

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

## 開發環境設置

### 安裝依賴
```bash
npm install
```

### 環境變數配置
複製 `.env.example` 到 `.env`：
```bash
cp .env.example .env
```

主要環境變數：
- `PUBLIC_GRAPHQL_ENDPOINT` - GraphQL API 端點
- `PUBLIC_WS_ENDPOINT` - WebSocket 端點（用於 subscriptions）

### 開發模式
```bash
npm run dev
```
應用程式將在 http://localhost:5173 啟動

### 建置生產版本
```bash
npm run build
npm run preview  # 預覽生產版本
```

## 專案結構

```
frontend/
├── src/
│   ├── routes/           # SvelteKit 路由
│   │   ├── +layout.svelte    # 根 layout（使用 Svelte 5 語法）
│   │   ├── +layout.ts        # SSR/CSR 配置
│   │   ├── +page.svelte      # 首頁
│   │   └── +error.svelte     # 錯誤頁面
│   ├── lib/
│   │   ├── components/   # 可重用元件
│   │   │   └── Button.svelte # Svelte 5 元件範例
│   │   ├── stores/       # Svelte stores
│   │   │   └── auth.svelte.ts # 認證 store（.svelte.ts 支援 runes）
│   │   └── utils/        # 工具函數
│   ├── app.html         # HTML 模板
│   ├── app.css          # 全域樣式（Tailwind）
│   └── app.d.ts         # TypeScript 定義
├── static/              # 靜態檔案
├── .env                 # 環境變數
├── svelte.config.js     # SvelteKit 配置
├── tailwind.config.js   # Tailwind 配置
├── postcss.config.js    # PostCSS 配置
└── tsconfig.json        # TypeScript 配置
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

## 可用腳本

- `npm run dev` - 啟動開發伺服器
- `npm run build` - 建置生產版本
- `npm run preview` - 預覽生產版本
- `npm run check` - 類型檢查
- `npm run lint` - ESLint 檢查
- `npm run format` - Prettier 格式化

## 注意事項

- 使用 Svelte 5 最新語法
- TypeScript strict mode 已啟用
- Tailwind CSS 已配置自定義主題色彩
- 路徑別名已設定（$lib, $components, $stores, $utils）