from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, Union
from fastapi import FastAPI, Depends, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter, BaseContext
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import init_db, close_db, get_async_session
from app.graphql.schema import schema
from app.graphql.dataloaders import DataLoaderContext
from app.core.security import decode_access_token


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    """Custom GraphQL context class that extends BaseContext"""
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._dataloaders = None
        self._user_id = None

    def __getitem__(self, key: str) -> Any:
        """Support dictionary-style access for backward compatibility"""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Support dictionary .get() method for backward compatibility"""
        return getattr(self, key, default)

    @property
    def dataloaders(self) -> DataLoaderContext:
        """Lazy initialization of dataloaders with user_id"""
        if self._dataloaders is None:
            self._dataloaders = DataLoaderContext(self.db_session, self.user_id)
        return self._dataloaders

    @property
    def user_id(self) -> Optional[int]:
        """Get current user ID from request or websocket headers"""
        # Try HTTP request first
        if self.request:
            authorization = self.request.headers.get("Authorization")
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

        # Try WebSocket connection
        elif self.websocket:
            if hasattr(self.websocket, "headers"):
                headers = dict(self.websocket.headers) if hasattr(self.websocket.headers, "__iter__") else {}
                authorization = headers.get("authorization") or headers.get("Authorization")
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