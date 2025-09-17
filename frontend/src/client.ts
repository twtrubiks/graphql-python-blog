import { HoudiniClient } from '$houdini'
import { browser } from '$app/environment'

// 取得 token 的函數
function getToken(): string | null {
    if (!browser) return null
    return localStorage.getItem('token')
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
    }
})