import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core import database
from app.core.database import Base
from app.models.user import User
from app.models.post import Post, PostStatus
from app.core.security import get_password_hash

@pytest.mark.asyncio
async def test_database_connection(test_session):
    """Test database connection is working."""
    result = await test_session.execute(select(1))
    assert result.scalar() == 1

@pytest.mark.asyncio
async def test_create_user(test_session):
    """Test creating a user in the database."""
    user = User(
        email="newuser@example.com",
        username="newuser",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.username == "newuser"
    assert user.is_active is True

@pytest.mark.asyncio
async def test_create_post(test_session, test_user):
    """Test creating a post in the database."""
    post = Post(
        title="Test Post",
        slug="test-post",
        content="This is test content",
        author_id=test_user.id,
        status=PostStatus.PUBLISHED
    )
    
    test_session.add(post)
    await test_session.commit()
    await test_session.refresh(post)
    
    assert post.id is not None
    assert post.title == "Test Post"
    assert post.author_id == test_user.id
    assert post.status == PostStatus.PUBLISHED

@pytest.mark.asyncio
async def test_user_post_relationship(test_session, test_user):
    """Test relationship between user and posts."""
    post1 = Post(
        title="First Post",
        slug="first-post",
        content="Content 1",
        author_id=test_user.id
    )
    post2 = Post(
        title="Second Post",
        slug="second-post",
        content="Content 2",
        author_id=test_user.id
    )
    
    test_session.add_all([post1, post2])
    await test_session.commit()
    
    result = await test_session.execute(
        select(Post).where(Post.author_id == test_user.id)
    )
    posts = result.scalars().all()
    
    assert len(posts) == 2
    assert all(post.author_id == test_user.id for post in posts)


@pytest.mark.asyncio
async def test_init_db_creates_all_tables(test_engine, monkeypatch):
    """開發模式啟動時以 init_db() 建立所有資料表；在空的 schema 裡執行來驗證"""
    schema = "init_db_check"
    async with test_engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {schema}"))
    engine = create_async_engine(
        test_engine.url, poolclass=NullPool, connect_args={"server_settings": {"search_path": schema}}
    )
    monkeypatch.setattr(database, "engine", engine)
    try:
        await database.init_db()

        async with test_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = :schema"),
                {"schema": schema},
            )
            assert {row[0] for row in result} == set(Base.metadata.tables)
    finally:
        await engine.dispose()
        async with test_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))


@pytest.mark.asyncio
async def test_close_db_disposes_engine(monkeypatch):
    disposed = []

    class FakeEngine:
        async def dispose(self):
            disposed.append(True)

    monkeypatch.setattr(database, "engine", FakeEngine())

    await database.close_db()

    assert disposed == [True]

