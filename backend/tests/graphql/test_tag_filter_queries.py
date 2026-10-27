"""測試標籤過濾查詢功能"""

from datetime import datetime, timedelta, timezone

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
                pageInfo { totalCount }
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
        result = response.json()["data"]["postsByTag"]
        assert result == {"edges": [], "pageInfo": {"totalCount": 0}}

class TestPostsByAnyTag:
    """postsByTags(requireAll: false)：含有任一標籤即符合"""

    QUERY = """
    query GetPostsByTags($tagSlugs: [String!]!) {
        postsByTags(tagSlugs: $tagSlugs, requireAll: false, limit: 10) {
            edges { node { title } }
            pageInfo { totalCount }
        }
    }
    """

    @pytest.mark.asyncio
    async def test_filter_posts_by_any_tag(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """符合任一標籤的文章各出現一次；草稿與已刪除的文章不列出也不計數"""
        python_tag = Tag(name="python", slug="python")
        web_tag = Tag(name="web", slug="web")
        rust_tag = Tag(name="rust", slug="rust")
        now = datetime.now(timezone.utc)

        def post(title, minutes_ago, tags, **kwargs):
            return Post(
                title=title,
                slug=title.lower().replace(" ", "-"),
                content=title,
                status=kwargs.pop("status", PostStatus.PUBLISHED),
                author_id=test_user.id,
                created_at=now - timedelta(minutes=minutes_ago),
                tags=tags,
                **kwargs,
            )

        test_session.add_all([
            post("Python And Web", 1, [python_tag, web_tag]),  # 兩個標籤都符合，只能出現一次
            post("Only Web", 2, [web_tag]),
            post("Only Python", 3, [python_tag]),
            post("Only Rust", 0, [rust_tag]),
            post("Python Draft", 0, [python_tag], status=PostStatus.DRAFT),
            post("Deleted Web", 0, [web_tag], deleted_at=now),
        ])
        await test_session.commit()

        response = await client.post(
            "/graphql",
            json={"query": self.QUERY, "variables": {"tagSlugs": ["python", "web"]}}
        )

        assert response.status_code == 200
        result = response.json()["data"]["postsByTags"]
        assert [edge["node"]["title"] for edge in result["edges"]] == [
            "Python And Web", "Only Web", "Only Python"
        ]
        assert result["pageInfo"]["totalCount"] == 3


class TestPostsByAllTags:
    """postsByTags(requireAll: true)：必須含有全部標籤"""

    QUERY = """
    query GetPostsByTags($tagSlugs: [String!]!) {
        postsByTags(tagSlugs: $tagSlugs, requireAll: true, limit: 10) {
            edges { node { title } }
            pageInfo { totalCount }
        }
    }
    """

    @pytest.fixture
    async def python_web_post(self, test_session: AsyncSession, test_user: User):
        test_session.add(Post(
            title="Python Web",
            slug="python-web",
            content="content",
            status=PostStatus.PUBLISHED,
            author_id=test_user.id,
            tags=[Tag(name="python", slug="python"), Tag(name="web", slug="web")],
        ))
        await test_session.commit()

    async def query(self, client: AsyncClient, tag_slugs: list[str]) -> dict:
        response = await client.post(
            "/graphql", json={"query": self.QUERY, "variables": {"tagSlugs": tag_slugs}}
        )
        return response.json()["data"]["postsByTags"]

    @pytest.mark.asyncio
    async def test_nonexistent_tag_matches_nothing(self, client: AsyncClient, python_web_post):
        """不存在的標籤不能被忽略：沒有文章同時擁有 python 與一個不存在的標籤"""
        result = await self.query(client, ["python", "no-such-tag"])

        assert result == {"edges": [], "pageInfo": {"totalCount": 0}}

    @pytest.mark.asyncio
    async def test_all_tags_missing(self, client: AsyncClient, python_web_post):
        result = await self.query(client, ["no-such-tag"])

        assert result == {"edges": [], "pageInfo": {"totalCount": 0}}

    @pytest.mark.asyncio
    async def test_duplicate_slugs(self, client: AsyncClient, python_web_post):
        """重複的 slug 只算一次，不會因此被當成有標籤不存在"""
        result = await self.query(client, ["python", "web", "python"])

        assert result == {"edges": [{"node": {"title": "Python Web"}}], "pageInfo": {"totalCount": 1}}
