/**
 * GraphQL 客戶端配置 - Houdini + SvelteKit 整合
 *
 * Houdini 是一個強大的 GraphQL 客戶端，專為 SvelteKit 設計：
 * - 編譯時優化：在構建時生成最優的查詢代碼
 * - 自動型別生成：從 GraphQL Schema 生成 TypeScript 類型
 * - 智能快取：自動管理查詢結果快取
 * - 深度整合：與 SvelteKit 的路由和 SSR 完美配合
 *
 * 本檔案處理：
 * 1. HTTP 請求配置（Query/Mutation）
 * 2. WebSocket 連線（Subscription）
 * 3. 認證 Token 管理
 * 4. 錯誤處理和重試邏輯
 */

import { HoudiniClient, subscription } from '$houdini'
import { browser } from '$app/environment'
import { createClient } from 'graphql-ws'
import { auth } from '$lib/stores/auth.svelte'
import { notifications } from '$lib/stores/notifications.svelte'
import { goto } from '$app/navigation'

// 取得有效 token 的函數
function getToken(): string | null {
    if (!browser) return null
    // 使用 auth.validToken 自動檢查過期並刷新
    return auth.validToken
}

/**
 * WebSocket 客戶端配置 - 用於 GraphQL Subscriptions
 *
 * Subscription 允許客戶端訂閱服務器的即時更新：
 * - 新評論通知
 * - 文章發布提醒
 * - 用戶狀態變更
 */
let wsClient: ReturnType<typeof createClient> | null = null

if (browser) {
    // 智能決定 WebSocket URL（支援開發和生產環境）
    const wsUrl = import.meta.env.VITE_WS_ENDPOINT ||
                  (window.location.protocol === 'https:'
                    ? `wss://${window.location.host}/graphql`
                    : 'ws://localhost:8000/graphql')

    wsClient = createClient({
        url: wsUrl,
        // 連線參數：每次連線時提供認證 token
        connectionParams: () => {
            const token = getToken()
            return token ? { Authorization: `Bearer ${token}` } : {}
        },
        // 自動重連策略：網路不穩定時自動恢復連線
        shouldRetry: () => true,
        retryAttempts: 5,
        retryWait: async (retries) => {
            // 指數退避算法：避免過度重試造成服務器壓力
            // 重試間隔：1s, 2s, 4s, 8s, 16s
            const delay = Math.min(1000 * Math.pow(2, retries), 16000)
            await new Promise(resolve => setTimeout(resolve, delay))
        },
        // 連線生命週期回調：用於偵錯和狀態管理
        on: {
            connected: () => console.log('[WS] Connected to GraphQL WebSocket'),
            error: (error) => console.error('[WS] Connection error:', error),
            closed: () => console.log('[WS] Connection closed'),
            connecting: () => console.log('[WS] Connecting...')
        }
    })
}

// v2 簡化的客戶端配置
// 注意：v2 正式版起 endpoint 不再傳給 HoudiniClient，改由 houdini.config.js 的 url 提供
export default new HoudiniClient({
    // v2: fetchParams 現在直接返回 RequestInit
    fetchParams() {
        const token = getToken()
        return {
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {})
            },
            // 只在瀏覽器端使用 credentials
            ...(browser ? { credentials: 'include' as RequestCredentials } : {})
        }
    },

    // 錯誤處理
    throwOnError: {
        operations: ['all'],
        error: (errors: any, ctx: any) => {
            if (!browser) return true;

            // 檢查是否為認證錯誤
            const hasAuthError = errors.some((error: any) =>
                error.message?.includes('Unauthorized') ||
                error.message?.includes('Token expired') ||
                error.message?.includes('Invalid token') ||
                error.extensions?.code === 'UNAUTHENTICATED'
            );

            if (hasAuthError) {
                console.log('[Client] Authentication error detected, logging out');
                // 登出並重定向
                auth.logout();
                notifications.error('登入已過期，請重新登入');
                goto('/login');
                return false; // 不拋出錯誤
            }

            return true; // 其他錯誤正常拋出
        }
    },

    // 配置 subscription 插件
    plugins: browser && wsClient ? [
        subscription(() => wsClient!)
    ] : []
})