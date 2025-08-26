import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.post import Post

@pytest.mark.asyncio
async def test_database_connection(test_session):
    """Test database connection is working."""
    result = await test_session.execute(select(1))
    assert result.scalar() == 1

@pytest.mark.asyncio
async def test_create_user(test_session):
    """Test creating a user in the database."""
    from app.core.security import get_password_hash
    
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
        content="This is test content",
        author_id=test_user.id,
        published=True
    )
    
    test_session.add(post)
    await test_session.commit()
    await test_session.refresh(post)
    
    assert post.id is not None
    assert post.title == "Test Post"
    assert post.author_id == test_user.id
    assert post.published is True

@pytest.mark.asyncio
async def test_user_post_relationship(test_session, test_user):
    """Test relationship between user and posts."""
    post1 = Post(
        title="First Post",
        content="Content 1",
        author_id=test_user.id
    )
    post2 = Post(
        title="Second Post",
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