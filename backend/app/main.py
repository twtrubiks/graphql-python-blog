from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import init_db, close_db, get_async_session
from app.graphql.schema import schema


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
    return {
        "db_session": db_session,
        "request": request
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