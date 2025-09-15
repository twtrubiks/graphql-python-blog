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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db, get_async_session
from app.main import app
from app.models.user import User
from app.models.post import Post, PostStatus
from app.core.security import get_password_hash, create_access_token
from tests.factories import UserFactory

TEST_DATABASE_URL = "postgresql+asyncpg://blog_user:blog_password@localhost:5444/test_blog"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

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