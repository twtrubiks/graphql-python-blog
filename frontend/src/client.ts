import { HoudiniClient, subscription } from '$houdini'
import { browser } from '$app/environment'
import { createClient } from 'graphql-ws'
import { auth } from '$lib/stores/auth.svelte'
import { notifications } from '$lib/stores/notifications.svelte'
import { goto } from '$app/navigation'

// 取得有效 token 的函數
function getToken(): string | null {
    if (!browser) return null
    // 使用 auth.validToken 自動檢查過期
    return auth.validToken
}

// WebSocket 客戶端配置 (僅在瀏覽器端)
let wsClient: ReturnType<typeof createClient> | null = null

if (browser) {
    // 決定 WebSocket URL
    const wsUrl = import.meta.env.VITE_WS_ENDPOINT ||
                  (window.location.protocol === 'https:'
                    ? `wss://${window.location.host}/graphql`
                    : 'ws://localhost:8000/graphql')

    wsClient = createClient({
        url: wsUrl,
        // 連線參數，用於認證
        connectionParams: () => {
            const token = getToken()
            return token ? { Authorization: `Bearer ${token}` } : {}
        },
        // 自動重連設置
        shouldRetry: () => true,
        retryAttempts: 5,
        retryWait: async (retries) => {
            // 指數退避：1s, 2s, 4s, 8s, 16s
            const delay = Math.min(1000 * Math.pow(2, retries), 16000)
            await new Promise(resolve => setTimeout(resolve, delay))
        },
        // 連線生命週期回調
        on: {
            connected: () => console.log('[WS] Connected to GraphQL WebSocket'),
            error: (error) => console.error('[WS] Connection error:', error),
            closed: () => console.log('[WS] Connection closed'),
            connecting: () => console.log('[WS] Connecting...')
        }
    })
}

// v2 簡化的客戶端配置
export default new HoudiniClient({
    // SSR 時使用內部地址（避免 CORS），瀏覽器使用環境變數配置的 endpoint
    url: browser
        ? (import.meta.env.VITE_GRAPHQL_ENDPOINT || 'http://localhost:8000/graphql')
        : 'http://127.0.0.1:8000/graphql',  // SSR 時使用 127.0.0.1 避免 DNS 解析問題

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