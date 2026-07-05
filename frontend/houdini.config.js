/// <references types="houdini-svelte">

/** @type {import('houdini').ConfigFile} */
const config = {
    // houdini 2.0 正式版預設 schemaPath 改為 .houdini/schema.graphql，
    // 明確指定以維持原本的位置
    schemaPath: './schema.graphql',

    // v2 正式版起，runtime endpoint 改由 config 提供（HoudiniClient 不再接受 url）。
    // 此檔會被打包進前後端 bundle，於各自環境求值：
    // 瀏覽器用環境變數配置的 endpoint，SSR 用 127.0.0.1 避免 DNS 解析問題
    url: typeof window !== 'undefined'
        ? (import.meta.env?.VITE_GRAPHQL_ENDPOINT || 'http://localhost:8000/graphql')
        : 'http://127.0.0.1:8000/graphql',

    // v2 新格式：將 schema 相關配置集中到 watchSchema
    watchSchema: {
        // 使用固定的後端地址，這個配置主要用於構建時拉取 schema
        url: 'http://127.0.0.1:8000/graphql',
        // 可選：輪詢間隔（開發時自動更新 schema）
        interval: 0,  // 0 表示不輪詢
        headers: {
            'Content-Type': 'application/json'
        }
    },

    // 插件配置
    plugins: {
        'houdini-svelte': {}
    },

    // 自定義 scalar 型別處理
    scalars: {
        DateTime: {
            type: 'Date',
            marshal: (val) => val.toISOString(),
            unmarshal: (val) => new Date(val)
        }
    },

    // 配置類型的 key 欄位，避免 Union Type 中的 id 類型衝突
    types: {
        // 禁用 SearchResult union 的自動 key 添加
        SearchResult: {
            keys: []
        },
        // 使用 slug 作為 PostType 的 key（在搜尋結果中）
        PostType: {
            keys: ['slug']
        },
        // 使用 username 作為 UserType 的 key（在搜尋結果中）
        UserType: {
            keys: ['username']
        }
    }
}

export default config