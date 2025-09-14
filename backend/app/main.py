from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
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

async def get_context(
    request: Request,
    db_session: AsyncSession = Depends(get_async_session)
):
    # 從 request 中獲取當前用戶 ID（如果有的話）
    user_id = None
    
    # 嘗試從 Authorization header 獲取 token
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # 移除 "Bearer " 前綴
        try:
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user_id = int(user_id)
        except Exception:
            # Token 無效或過期，保持 user_id 為 None
            pass
    
    # 創建 DataLoader 上下文
    dataloader_context = DataLoaderContext(db_session, user_id)
    
    return {
        "db_session": db_session,
        "request": request,
        "dataloaders": dataloader_context
    }

graphql_app = GraphQLRouter(
    schema,
    path="/graphql",
    graphql_ide="graphiql" if settings.DEBUG else None,
    context_getter=get_context,
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