# GraphQL 部落格平台 - 系統架構文件

## 目錄

- [架構概述](#架構概述)
- [C4 模型架構圖](#c4-模型架構圖)
  - [Level 1: System Context](#level-1-system-context)
  - [Level 2: Container Diagram](#level-2-container-diagram)
  - [Level 3: Component Diagram](#level-3-component-diagram)
  - [Level 4: Code Diagram](#level-4-code-diagram)
- [技術決策](#技術決策)
- [資料流程](#資料流程)
- [安全架構](#安全架構)
- [效能考量](#效能考量)

## 架構概述

本系統採用現代化的前後端分離架構，以 GraphQL 作為 API 層，實現高效的資料查詢與變更。後端使用 Python 3.13 搭配 FastAPI 框架，前端使用 SvelteKit 與 Svelte 5，資料庫採用 PostgreSQL 搭配 pgvector 擴充套件支援向量搜尋。

### 技術元件分類

#### 核心元件（必需）
- **PostgreSQL 16** - 主要資料庫
- **FastAPI** - Web 框架
- **Strawberry** - GraphQL 函式庫
- **SQLAlchemy 2.0** - ORM

#### 選用元件（增強功能）
- **pgvector** - 向量搜尋（進階 AI 功能）

### 核心原則

1. **關注點分離**: 清晰的層次架構，各層職責明確
2. **可測試性**: 採用 TDD 開發，確保程式碼品質
3. **可擴展性**: 模組化設計，易於新增功能
4. **效能優先**: 使用異步處理、快取策略、查詢優化

## C4 模型架構圖

### Level 1: System Context

系統整體環境圖，展示系統與外部使用者及系統的互動關係。

```mermaid
graph TB
    subgraph "GraphQL Blog Platform"
        System[Blog System]
    end

    User[一般使用者]
    Author[內容創作者]
    Admin[系統管理員]

    Email[Email Service]
    Storage[Cloud Storage]
    AI[AI Service<br/>OpenAI/Local Model]

    User --> System
    Author --> System
    Admin --> System

    System --> Email
    System --> Storage
    System --> AI

    style System fill:#1168bd,stroke:#333,stroke-width:4px,color:#fff
    style User fill:#08427b,stroke:#333,stroke-width:2px,color:#fff
    style Author fill:#08427b,stroke:#333,stroke-width:2px,color:#fff
    style Admin fill:#08427b,stroke:#333,stroke-width:2px,color:#fff
```

### Level 2: Container Diagram

容器層級圖，展示主要的技術組件及其互動方式。

```mermaid
graph TB
    subgraph "Client Side"
        WebApp[Web Application<br/>SvelteKit + Svelte 5<br/>Houdini GraphQL Client]
    end

    subgraph "Server Side"
        API[API Server<br/>FastAPI + Strawberry<br/>Python 3.13]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL 16<br/>+ pgvector)]
        FileStore[File Storage<br/>Local/S3]
    end

    WebApp -->|GraphQL over HTTP/HTTPS| API
    WebApp -->|WebSocket| API
    API --> DB
    API --> FileStore

    style WebApp fill:#1168bd,stroke:#333,stroke-width:2px,color:#fff
    style API fill:#1168bd,stroke:#333,stroke-width:2px,color:#fff
    style DB fill:#999,stroke:#333,stroke-width:2px,color:#fff
```

### Level 3: Component Diagram

組件層級圖，展示後端 API Server 的內部結構。

```mermaid
graph TB
    subgraph "API Server Components"
        subgraph "API Layer"
            GQL[GraphQL Schema<br/>Strawberry]
            REST[REST Endpoints<br/>File Upload]
        end

        subgraph "Business Logic"
            Auth[Authentication<br/>Service]
            PostSvc[Post Service]
            UserSvc[User Service]
            CommentSvc[Comment Service]
            SearchSvc[Search Service]
            VectorSvc[Vector Service<br/>pgvector]
        end

        subgraph "Data Access"
            Models[SQLAlchemy Models]
            Repos[Repositories]
        end

        subgraph "Cross-Cutting"
            MW[Middleware<br/>CORS, Auth, Logging]
            Valid[Validators]
            Utils[Utilities]
        end
    end

    GQL --> Auth
    GQL --> PostSvc
    GQL --> UserSvc
    GQL --> CommentSvc
    GQL --> SearchSvc

    REST --> PostSvc

    PostSvc --> VectorSvc
    SearchSvc --> VectorSvc

    PostSvc --> Repos
    UserSvc --> Repos
    CommentSvc --> Repos
    Auth --> Repos

    Repos --> Models

    style GQL fill:#1168bd,stroke:#333,stroke-width:2px,color:#fff
    style Auth fill:#52b788,stroke:#333,stroke-width:2px,color:#fff
    style PostSvc fill:#52b788,stroke:#333,stroke-width:2px,color:#fff
    style Models fill:#999,stroke:#333,stroke-width:2px,color:#fff
```

### Level 4: Code Diagram

核心類別圖，展示主要的資料模型與其關係。

```mermaid
classDiagram
    class User {
        +UUID id
        +str email
        +str username
        +str password_hash
        +str bio
        +str avatar_url
        +datetime created_at
        +create_post()
        +follow_user()
    }

    class Post {
        +UUID id
        +str title
        +str slug
        +str content
        +str excerpt
        +UUID author_id
        +PostStatus status
        +datetime created_at
        +datetime updated_at
        +vector embedding
        +publish()
        +add_comment()
        +get_similar_posts()
    }

    class Comment {
        +UUID id
        +str content
        +UUID author_id
        +UUID post_id
        +datetime created_at
    }

    class Tag {
        +UUID id
        +str name
        +str slug
    }

    class Like {
        +UUID user_id
        +UUID post_id
        +datetime created_at
    }

    class Follow {
        +UUID follower_id
        +UUID following_id
        +datetime created_at
    }

    User "1" --> "*" Post : writes
    User "1" --> "*" Comment : writes
    User "*" --> "*" User : follows
    User "*" --> "*" Post : likes
    Post "1" --> "*" Comment : has
    Post "*" --> "*" Tag : tagged with
    Post "1" --> "1" User : written by
```

## 技術決策

### 為什麼選擇 GraphQL？

1. **精確的資料獲取**: 客戶端可以準確指定需要的資料
2. **減少請求次數**: 一次請求獲取多個資源
3. **強型別**: Schema 提供清晰的 API 契約
4. **自文件化**: Schema 即文件

### 為什麼選擇 FastAPI + Strawberry？

1. **現代 Python**: 充分利用 Type Hints
2. **異步支援**: 原生異步處理提升效能
3. **自動文件**: 自動生成 API 文件
4. **開發體驗**: 優秀的開發者體驗

### 為什麼選擇 PostgreSQL + pgvector？

1. **關聯式資料**: 部落格資料本質上是關聯式的
2. **ACID 特性**: 確保資料一致性
3. **向量搜尋**: pgvector 支援語義搜尋
4. **成熟穩定**: PostgreSQL 是最可靠的開源資料庫

### 為什麼選擇 SvelteKit + Svelte 5？

1. **編譯時優化**: 無虛擬 DOM，效能更好
2. **簡潔語法**: 更少的樣板代碼
3. **Runes 系統**: Svelte 5 的響應式更強大
4. **內建功能**: 路由、SSR 等功能內建

## 資料流程

### 查詢流程 (Query)

```mermaid
sequenceDiagram
    participant Client
    participant GraphQL
    participant Service
    participant Repository
    participant Database

    Client->>GraphQL: GraphQL Query
    GraphQL->>Service: Call Service Method
    Service->>Repository: Query Data
    Repository->>Database: SQL Query
    Database-->>Repository: Result Set
    Repository-->>Service: Domain Objects
    Service-->>GraphQL: Return Data
    GraphQL-->>Client: GraphQL Response
```

### 變更流程 (Mutation)

```mermaid
sequenceDiagram
    participant Client
    participant GraphQL
    participant Auth
    participant Service
    participant Repository
    participant Database

    Client->>GraphQL: GraphQL Mutation
    GraphQL->>Auth: Verify JWT
    Auth-->>GraphQL: User Context
    GraphQL->>Service: Execute Business Logic
    Service->>Repository: Persist Changes
    Repository->>Database: INSERT/UPDATE/DELETE
    Database-->>Repository: Confirmation
    Repository-->>Service: Updated Entity
    Service-->>GraphQL: Return Result
    GraphQL-->>Client: GraphQL Response
```

### 向量搜尋流程

```mermaid
sequenceDiagram
    participant Client
    participant GraphQL
    participant SearchService
    participant VectorService
    participant EmbeddingModel
    participant Database

    Client->>GraphQL: Search Query
    GraphQL->>SearchService: Search Request
    SearchService->>VectorService: Generate Embedding
    VectorService->>EmbeddingModel: Text to Vector
    EmbeddingModel-->>VectorService: Vector Embedding
    VectorService->>Database: Vector Similarity Search
    Database-->>VectorService: Similar Documents
    VectorService-->>SearchService: Search Results
    SearchService-->>GraphQL: Formatted Results
    GraphQL-->>Client: Search Response
```

## 安全架構

### 認證與授權

```mermaid
graph TB
    subgraph "Authentication Flow"
        Login[Login Endpoint]
        JWT[JWT Generation]
        Verify[JWT Verification]
        Refresh[Token Refresh]
    end

    subgraph "Authorization"
        RBAC[Role-Based Access]
        Ownership[Resource Ownership]
        Permissions[Permission Check]
    end

    subgraph "Security Layers"
        Validation[Input Validation]
        Sanitize[Content Sanitization]
        CORS[CORS Policy]
    end

    Login --> JWT
    JWT --> Verify
    Verify --> RBAC
    RBAC --> Ownership
    Ownership --> Permissions

    style Login fill:#e63946,stroke:#333,stroke-width:2px,color:#fff
    style RBAC fill:#f77f00,stroke:#333,stroke-width:2px,color:#fff
```

### 安全措施

1. **JWT Token 管理**
   - Access Token: 15 分鐘過期
   - Refresh Token: 7 天過期
   - Token 黑名單機制

2. **輸入驗證**
   - GraphQL Schema 層級驗證
   - Service 層業務邏輯驗證
   - SQL Injection 防護 (ORM)

3. **內容安全**
   - XSS 防護：HTML 消毒
   - CSRF 防護：Token 驗證
   - File Upload：類型與大小限制

4. **存取控制**
   - CORS 設定：限制來源
   - HTTPS：建議使用（教學環境可選）

## 效能考量

### 查詢優化策略

1. **DataLoader Pattern**
   - 解決 N+1 查詢問題
   - 批次載入關聯資料

2. **資料庫索引**
   ```sql
   -- 常用查詢索引
   CREATE INDEX idx_posts_author_id ON posts(author_id);
   CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
   CREATE INDEX idx_posts_status ON posts(status) WHERE status = 'published';

   -- 全文搜尋索引
   CREATE INDEX idx_posts_search ON posts USING gin(to_tsvector('english', title || ' ' || content));

   -- 向量搜尋索引
   CREATE INDEX idx_posts_embedding ON posts USING ivfflat (embedding vector_cosine_ops);
   ```

3. **快取策略**
   - GraphQL 查詢結果快取（可選）
   - CDN 靜態資源快取

### 異步處理

1. **異步 I/O**
   - FastAPI 異步端點
   - SQLAlchemy 異步 Session

2. **異步操作**
   - 向量生成（使用異步函式）
   - 圖片處理（使用異步函式）

### 監控指標

1. **應用程式指標**
   - API 回應時間
   - 錯誤率
   - 請求量

2. **資料庫指標**
   - 查詢效能
   - 連線池使用率
   - 慢查詢日誌

3. **系統指標**
   - CPU 使用率
   - 記憶體使用率
   - 磁碟 I/O

## 部署架構

### 開發環境

```mermaid
graph LR
    Dev[開發機器]
    Docker[Docker Compose]

    subgraph "Containers"
        App[App Container]
        DB[PostgreSQL Container]
    end

    Dev --> Docker
    Docker --> App
    Docker --> DB
```


## 擴展性設計

### 水平擴展

1. **無狀態設計**: API Server 無狀態，可水平擴展
2. **資料庫讀寫分離**: Master-Replica 架構

### 垂直擴展

1. **資料庫優化**: 查詢優化、索引調整
2. **連線池管理**: 優化連線池大小
3. **資源調配**: 根據負載調整資源

### 微服務預留

雖然初期是單體架構，但設計上預留了拆分可能：

1. **Service 層抽象**: 易於抽取為獨立服務
2. **訊息佇列預留**: 可加入 RabbitMQ/Kafka
3. **API Gateway 預留**: 可加入 Kong/Traefik

## 技術債管理

### 已識別的技術債

1. **初期簡化**
   - 未實作完整的快取失效策略
   - 簡化的錯誤處理
   - 基礎的日誌記錄

2. **待優化項目**
   - 查詢複雜度限制
   - 更細緻的權限控制
   - 完整的審計日誌

### 償還策略

1. **持續重構**: 每個 Sprint 20% 時間
2. **測試覆蓋**: 逐步提高測試覆蓋率
3. **文件更新**: 保持架構文件同步

---

本文件將隨著專案演進持續更新，確保架構決策的透明度與可追溯性。