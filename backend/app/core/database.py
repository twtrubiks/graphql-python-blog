from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

def create_session_factory(bind) -> async_sessionmaker[AsyncSession]:
    """建立 session factory。測試以同一份設定連到測試資料庫，行為才會和正式環境一致"""
    return async_sessionmaker(
        bind,
        class_=AsyncSession,
        # commit 後物件不過期：resolver 在 commit 之後還會讀取屬性，過期就會觸發 async 環境不允許的延遲載入
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


AsyncSessionLocal = create_session_factory(engine)

Base = declarative_base()

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """每個請求一個 session，請求結束時由 async with 關閉"""
    async with AsyncSessionLocal() as session:
        yield session

def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """給請求結束後才執行的背景工作使用：request session 屆時已關閉，必須自己開新的 session。
    以 dependency 提供，測試才能換成測試資料庫。"""
    return AsyncSessionLocal

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    await engine.dispose()