import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any

def random_string(length: int = 10) -> str:
    """Generate a random string of specified length."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def random_email() -> str:
    """Generate a random email address."""
    return f"{random_string()}@example.com"

def random_username() -> str:
    """Generate a random username."""
    return f"user_{random_string(8)}"

def random_datetime(
    start_date: datetime = None,
    end_date: datetime = None
) -> datetime:
    """Generate a random datetime between start and end dates."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=365)
    if not end_date:
        end_date = datetime.now()
    
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return start_date + timedelta(days=random_days)

def create_test_user_data() -> Dict[str, Any]:
    """Create test user data."""
    return {
        "email": random_email(),
        "username": random_username(),
        "password": "Test123!@#",
        "full_name": f"Test {random_string(5)}"
    }

def create_test_post_data() -> Dict[str, Any]:
    """Create test post data."""
    return {
        "title": f"Test Post {random_string(10)}",
        "content": f"This is test content {random_string(50)}",
        "published": random.choice([True, False]),
        "tags": [random_string(5) for _ in range(random.randint(1, 5))]
    }

def create_test_comment_data() -> Dict[str, Any]:
    """Create test comment data."""
    return {
        "content": f"This is a test comment {random_string(30)}"
    }

async def create_test_posts(session, user, count: int = 5):
    """Create multiple test posts."""
    from app.models.post import Post
    
    posts = []
    for i in range(count):
        post = Post(
            title=f"Test Post {i + 1}",
            content=f"Content for test post {i + 1}",
            author_id=user.id,
            published=i % 2 == 0
        )
        session.add(post)
        posts.append(post)
    
    await session.commit()
    for post in posts:
        await session.refresh(post)
    
    return posts

async def create_test_comments(session, post, user, count: int = 3):
    """Create multiple test comments."""
    from app.models.comment import Comment
    
    comments = []
    for i in range(count):
        comment = Comment(
            content=f"Test comment {i + 1}",
            post_id=post.id,
            author_id=user.id
        )
        session.add(comment)
        comments.append(comment)
    
    await session.commit()
    for comment in comments:
        await session.refresh(comment)
    
    return comments