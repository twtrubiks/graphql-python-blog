"""
GraphQL Blog Platform - 主應用程式入口
這是一個展示 GraphQL + Python 最佳實踐的教學專案

技術棧：
- FastAPI: 現代化的 Python Web 框架，支援異步和自動文檔生成
- Strawberry: Python GraphQL 函式庫，提供類型安全的 Schema 定義
- SQLAlchemy 2.0: 強大的 ORM，支援異步操作
- PostgreSQL: 關聯式資料庫

主要特色：
1. GraphQL API 設計模式
2. DataLoader 解決 N+1 查詢問題
3. WebSocket 支援即時通訊
4. JWT 認證機制
5. 異步處理提升效能
"""

from contextlib import asynccontextmanager
from typing import Optional, Any
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter, BaseContext
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import init_db, close_db, get_async_session
from app.graphql.schema import schema
from app.graphql.dataloaders import DataLoaderContext
from app.core.security import decode_access_token

# 哨兵值，用於區分「未初始化」和「None」
_UNSET = object()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理
    - 啟動時：初始化資料庫連線池
    - 關閉時：清理資源，關閉連線

    使用 asynccontextmanager 確保資源正確管理
    """
    if settings.DEBUG:
        print("Initializing database...")
        await init_db()
        print("Database initialized!")
    yield
    await close_db()
    print("Database connection closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="GraphQL Blog Platform API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GraphQLContext(BaseContext):
    """
    自定義 GraphQL Context - GraphQL 請求的上下文物件

    Context 是 GraphQL 中的重要概念，每個請求都會創建一個 Context，
    用於在不同的 resolver 之間共享狀態和資源。

    主要功能：
    1. 資料庫連線管理：每個請求使用獨立的資料庫 session
    2. DataLoader 管理：解決 N+1 查詢問題的關鍵
    3. 用戶認證狀態：從 JWT token 提取用戶資訊
    4. 請求級別的快取：避免重複查詢
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._dataloaders = None  # 延遲初始化，提升效能
        self._user_id: Any = _UNSET  # 使用哨兵值區分「未初始化」和「None」

    def __getitem__(self, key: str) -> Any:
        """Support dictionary-style access for backward compatibility"""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Support dictionary .get() method for backward compatibility"""
        return getattr(self, key, default)

    @property
    def dataloaders(self) -> DataLoaderContext:
        """
        延遲初始化 DataLoader

        DataLoader 是 Facebook 開發的模式，用於解決 GraphQL 的 N+1 查詢問題。
        它會自動批次處理和快取查詢，大幅提升效能。

        例如：查詢 10 篇文章的作者時，不會執行 10 次查詢，
        而是收集所有作者 ID，執行 1 次批次查詢。
        """
        if self._dataloaders is None:
            self._dataloaders = DataLoaderContext(self.db_session, self.user_id)
        return self._dataloaders

    def _decode_user_id_from_authorization(self, authorization: Optional[str]) -> Optional[int]:
        """從 Authorization header 解碼用戶 ID"""
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            try:
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        return int(user_id)
            except Exception:
                pass
        return None

    @property
    def user_id(self) -> Optional[int]:
        """Get current user ID from request or websocket headers (cached)"""
        # 如果已解碼過，直接返回快取結果
        if self._user_id is not _UNSET:
            return self._user_id

        result: Optional[int] = None

        # Try HTTP request first
        if self.request:
            authorization = self.request.headers.get("Authorization")
            result = self._decode_user_id_from_authorization(authorization)
        # Try WebSocket connection
        elif self.websocket:
            if hasattr(self.websocket, "headers"):
                headers = dict(self.websocket.headers) if hasattr(self.websocket.headers, "__iter__") else {}
                authorization = headers.get("authorization") or headers.get("Authorization")
                result = self._decode_user_id_from_authorization(authorization)

        # 快取結果
        self._user_id = result
        return result

async def get_context(
    db_session: AsyncSession = Depends(get_async_session),
) -> GraphQLContext:
    """Create GraphQL context with database session"""
    # Return the context - dataloaders will be initialized lazily
    return GraphQLContext(db_session)

# 使用統一的 context getter
graphql_app = GraphQLRouter(
    schema,
    path="/graphql",
    graphql_ide="graphiql" if settings.DEBUG else None,
    context_getter=get_context,
    subscription_protocols=[
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        GRAPHQL_WS_PROTOCOL,
    ]
)

app.include_router(graphql_app, prefix="")

@app.get("/")
async def root():
    return {
        "message": "GraphQL Blog API", 
        "graphql_endpoint": "/graphql",
        "graphql_playground": "/graphql" if settings.DEBUG else None
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}