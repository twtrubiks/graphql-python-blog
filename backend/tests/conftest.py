import os
import sys
import asyncio
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from slugify import slugify
import asyncpg

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db, get_async_session
from app.main import app
from app.models.user import User
from app.models.post import Post, PostStatus
from app.core.security import get_password_hash, create_access_token
from app.core.config import settings
from tests.factories import UserFactory

# 從環境變數讀取資料庫配置
DB_HOST = settings.DB_HOST
DB_PORT = settings.DB_PORT
DB_USER = settings.DB_USER
DB_PASSWORD = settings.DB_PASSWORD
TEST_DB_NAME = settings.TEST_DB_NAME
TEST_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """自動創建測試資料庫，在所有測試開始前執行"""
    conn = None
    try:
        # 連接到 postgres 資料庫（默認資料庫）
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"
        )

        # 檢查測試資料庫是否存在
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
            TEST_DB_NAME
        )

        if exists:
            # 終止所有連接到測試資料庫的會話
            await conn.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{TEST_DB_NAME}'
                AND pid <> pg_backend_pid()
            """)

            # 刪除現有的測試資料庫
            await conn.execute(f'DROP DATABASE IF EXISTS {TEST_DB_NAME}')

        # 創建新的測試資料庫
        await conn.execute(f'CREATE DATABASE {TEST_DB_NAME}')

        print(f"\n✅ 測試資料庫 '{TEST_DB_NAME}' 已自動創建")

    except Exception as e:
        pytest.exit(f"❌ 無法創建測試資料庫：{e}", returncode=1)

    finally:
        if conn:
            await conn.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine - session scope for better performance."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    # 只在測試 session 開始時創建一次表格
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 測試 session 結束時清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async def override_get_db():
        async with async_session_maker() as session:
            yield session
            await session.commit()

    async def override_get_async_session():
        async with async_session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_session] = override_get_async_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def authenticated_client(test_engine, test_user) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated test client."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async def override_get_db():
        async with async_session_maker() as session:
            yield session
            await session.commit()

    async def override_get_async_session():
        async with async_session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_session] = override_get_async_session

    access_token = create_access_token(data={"sub": str(test_user.id)})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({"Authorization": f"Bearer {access_token}"})
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(test_engine):
    """Create a test user."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
async def test_admin_user(test_engine):
    """Create a test admin user."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        admin = User(
            email="admin@example.com",
            username="admin",
            hashed_password=get_password_hash("adminpassword"),
            is_active=True,
            is_superuser=True
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin

@pytest_asyncio.fixture
async def async_session(test_session):
    """Alias for test_session to match test expectations."""
    return test_session

@pytest_asyncio.fixture
async def test_post(test_engine, test_user):
    """Create a test post."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        post = Post(
            title="Test Post",
            slug=slugify("Test Post"),
            content="This is a test post content.",
            excerpt="Test excerpt",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

@pytest_asyncio.fixture
async def user_factory(test_engine):
    """Factory for creating test users."""
    UserFactory._counter = 0  # Reset counter for each test

    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    class Factory:
        async def create(self, **kwargs):
            async with async_session_maker() as session:
                user = await UserFactory.create(session, **kwargs)
                await session.commit()
                await session.refresh(user)
                return user

    return Factory()

@pytest_asyncio.fixture(autouse=True, scope="function")
async def cleanup_db(test_engine):
    """自動清理每個測試後的資料庫資料，但保留表結構。"""
    yield  # 執行測試

    # 測試結束後清理所有資料（但不刪除表格）
    async with test_engine.begin() as conn:
        # 按照反向順序刪除資料，避免外鍵約束問題
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())