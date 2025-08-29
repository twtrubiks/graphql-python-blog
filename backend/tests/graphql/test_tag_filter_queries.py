"""測試標籤過濾查詢功能"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.post import Post, PostStatus
from app.models.tag import Tag, post_tags


class TestPostTagFilter:
    """測試文章標籤過濾"""
    
    @pytest.mark.asyncio
    async def test_filter_posts_by_tag(
        self,
        authenticated_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """測試根據標籤過濾文章"""
        # 創建標籤
        python_tag = Tag(name="python", slug="python")
        django_tag = Tag(name="django", slug="django")
        fastapi_tag = Tag(name="fastapi", slug="fastapi")
        test_session.add_all([python_tag, django_tag, fastapi_tag])
        
        # 創建文章
        post1 = Post(
            title="Python Basics",
            slug="python-basics",
            content="Learn Python",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        post2 = Post(
            title="Django Tutorial",
            slug="django-tutorial",
            content="Learn Django",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        post3 = Post(
            title="FastAPI Guide",
            slug="fastapi-guide",
            content="Learn FastAPI",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        test_session.add_all([post1, post2, post3])
        await test_session.commit()
        
        # 建立關聯
        # post1: python
        await test_session.execute(
            post_tags.insert().values(post_id=post1.id, tag_id=python_tag.id)
        )
        # post2: python, django
        await test_session.execute(
            post_tags.insert().values(post_id=post2.id, tag_id=python_tag.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post2.id, tag_id=django_tag.id)
        )
        # post3: fastapi
        await test_session.execute(
            post_tags.insert().values(post_id=post3.id, tag_id=fastapi_tag.id)
        )
        await test_session.commit()
        
        # 查詢含有 python 標籤的文章
        query = """
        query GetPostsByTag($tagSlug: String!) {
            postsByTag(tagSlug: $tagSlug, limit: 10) {
                edges {
                    node {
                        id
                        title
                        tags {
                            name
                        }
                    }
                }
            }
        }
        """
        
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"tagSlug": "python"}
            }
        )
        
        assert response.status_code == 200
        edges = response.json()["data"]["postsByTag"]["edges"]
        assert len(edges) == 2
        
        titles = {edge["node"]["title"] for edge in edges}
        assert "Python Basics" in titles
        assert "Django Tutorial" in titles
        assert "FastAPI Guide" not in titles
    
    @pytest.mark.asyncio
    async def test_filter_posts_by_multiple_tags(
        self,
        authenticated_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """測試根據多個標籤過濾文章"""
        # 創建標籤
        python_tag = Tag(name="python", slug="python")
        web_tag = Tag(name="web", slug="web")
        test_session.add_all([python_tag, web_tag])
        
        # 創建文章
        post1 = Post(
            title="Python Web Development",
            slug="python-web-dev",
            content="Python for web",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        post2 = Post(
            title="Python Scripts",
            slug="python-scripts",
            content="Python scripts",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        post3 = Post(
            title="JavaScript Web",
            slug="js-web",
            content="JS for web",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        test_session.add_all([post1, post2, post3])
        await test_session.commit()
        
        # 建立關聯
        # post1: python, web
        await test_session.execute(
            post_tags.insert().values(post_id=post1.id, tag_id=python_tag.id)
        )
        await test_session.execute(
            post_tags.insert().values(post_id=post1.id, tag_id=web_tag.id)
        )
        # post2: python
        await test_session.execute(
            post_tags.insert().values(post_id=post2.id, tag_id=python_tag.id)
        )
        # post3: web
        await test_session.execute(
            post_tags.insert().values(post_id=post3.id, tag_id=web_tag.id)
        )
        await test_session.commit()
        
        # 查詢同時含有 python 和 web 標籤的文章
        query = """
        query GetPostsByTags($tagSlugs: [String!]!) {
            postsByTags(tagSlugs: $tagSlugs, requireAll: true, limit: 10) {
                edges {
                    node {
                        id
                        title
                    }
                }
            }
        }
        """
        
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"tagSlugs": ["python", "web"]}
            }
        )
        
        assert response.status_code == 200
        edges = response.json()["data"]["postsByTags"]["edges"]
        assert len(edges) == 1
        assert edges[0]["node"]["title"] == "Python Web Development"
    
    @pytest.mark.asyncio
    async def test_filter_posts_by_nonexistent_tag(
        self,
        authenticated_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """測試使用不存在的標籤過濾"""
        # 創建一個文章
        post = Post(
            title="Test Post",
            slug="test-post",
            content="Content",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id
        )
        test_session.add(post)
        await test_session.commit()
        
        # 查詢不存在的標籤
        query = """
        query GetPostsByTag($tagSlug: String!) {
            postsByTag(tagSlug: $tagSlug, limit: 10) {
                edges {
                    node {
                        id
                        title
                    }
                }
            }
        }
        """
        
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"tagSlug": "nonexistent"}
            }
        )
        
        assert response.status_code == 200
        edges = response.json()["data"]["postsByTag"]["edges"]
        assert len(edges) == 0