/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_GRAPHQL_ENDPOINT: string
    readonly VITE_WS_ENDPOINT: string
    // 其他 VITE_ 開頭的環境變數
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}