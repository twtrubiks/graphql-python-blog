from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.graphql.schema import schema

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="GraphQL Blog Platform API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphql_app = GraphQLRouter(
    schema,
    path="/graphql",
    graphql_ide="graphiql" if settings.DEBUG else None,
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