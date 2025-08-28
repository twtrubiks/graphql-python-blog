"""測試文章查詢功能

按照 TDD 方法，先寫測試再實作功能
"""

import pytest
from tests.factories import UserFactory, PostFactory
from app.models.post import PostStatus


class TestPostQuery:
    """測試單一文章查詢"""
    
    @pytest.mark.asyncio
    async def test_get_post_by_id_success(
        self, 
        client, 
        test_session
    ):
        """測試：成功查詢單一文章"""
        # Arrange - 建立測試資料
        user = await UserFactory.create(test_session)
        post = await PostFactory.create(
            test_session,
            author_id=user.id,
            title="GraphQL 教學",
            content="這是一篇關於 GraphQL 的教學文章",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()
        
        # Act - 執行查詢
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                    content
                    excerpt
                    slug
                    status
                    author {
                        id
                        username
                        bio
                    }
                    createdAt
                    updatedAt
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        
        post_data = data["data"]["post"]
        assert str(post_data["id"]) == str(post.id)
        assert post_data["title"] == "GraphQL 教學"
        assert post_data["content"] == "這是一篇關於 GraphQL 的教學文章"
        # Excerpt should be the content itself since it's short
        assert post_data["excerpt"] == "這是一篇關於 GraphQL 的教學文章"
        assert post_data["slug"] == post.slug
        assert post_data["status"] == "PUBLISHED"
        assert str(post_data["author"]["id"]) == str(user.id)
        assert post_data["author"]["username"] == user.username
    
    @pytest.mark.asyncio
    async def test_get_post_not_found(self, client):
        """測試：查詢不存在的文章"""
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": "999999"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["post"] is None
    
    @pytest.mark.asyncio
    async def test_get_draft_post_by_author(
        self,
        client,
        test_session
    ):
        """測試：作者可以查看自己的草稿"""
        # Arrange
        user = await UserFactory.create(test_session)
        post = await PostFactory.create(
            test_session,
            author_id=user.id,
            title="我的草稿",
            status=PostStatus.DRAFT
        )
        await test_session.commit()
        
        # 使用作者的認證 headers
        from app.core.security import create_access_token
        access_token = create_access_token(data={"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Act
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                    status
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            },
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        
        post_data = data["data"]["post"]
        assert str(post_data["id"]) == str(post.id)
        assert post_data["title"] == "我的草稿"
        assert post_data["status"] == "DRAFT"
    
    @pytest.mark.asyncio
    async def test_cannot_get_others_draft(
        self,
        client,
        test_session
    ):
        """測試：無法查看他人的草稿"""
        # Arrange
        author = await UserFactory.create(test_session)
        other_user = await UserFactory.create(test_session)
        
        post = await PostFactory.create(
            test_session,
            author_id=author.id,
            title="他人的草稿",
            status=PostStatus.DRAFT
        )
        await test_session.commit()
        
        # 使用其他用戶的認證
        from app.core.security import create_access_token
        access_token = create_access_token(data={"sub": str(other_user.id)})
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Act
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                    status
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            },
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["post"] is None


class TestPostsQuery:
    """測試文章列表查詢"""
    
    @pytest.mark.asyncio
    async def test_get_posts_with_pagination(
        self,
        client,
        test_session
    ):
        """測試：文章列表查詢與分頁"""
        # Arrange - 建立多篇文章
        user = await UserFactory.create(test_session)
        
        # 建立 15 篇已發布文章
        for i in range(15):
            await PostFactory.create(
                test_session,
                author_id=user.id,
                title=f"文章 {i+1}",
                status=PostStatus.PUBLISHED
            )
        await test_session.commit()
        
        # Act - 查詢第一頁
        query = """
            query GetPosts($page: Int!, $limit: Int!) {
                posts(page: $page, limit: $limit) {
                    edges {
                        node {
                            id
                            title
                            excerpt
                            author {
                                username
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        totalCount
                        currentPage
                        totalPages
                    }
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"page": 1, "limit": 10}
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        
        posts_data = data["data"]["posts"]
        assert len(posts_data["edges"]) == 10
        assert posts_data["pageInfo"]["hasNextPage"] is True
        assert posts_data["pageInfo"]["hasPreviousPage"] is False
        assert posts_data["pageInfo"]["totalCount"] == 15
        assert posts_data["pageInfo"]["currentPage"] == 1
        assert posts_data["pageInfo"]["totalPages"] == 2
    
    @pytest.mark.asyncio
    async def test_posts_only_show_published(
        self,
        client,
        test_session
    ):
        """測試：只顯示已發布的文章"""
        # Arrange
        user = await UserFactory.create(test_session)
        
        # 建立不同狀態的文章
        published_posts = []
        for i in range(3):
            post = await PostFactory.create(
                test_session,
                author_id=user.id,
                title=f"已發布 {i+1}",
                status=PostStatus.PUBLISHED
            )
            published_posts.append(post)
        
        # 建立草稿和已封存文章（不應顯示）
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="草稿文章",
            status=PostStatus.DRAFT
        )
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="已封存文章",
            status=PostStatus.ARCHIVED
        )
        
        await test_session.commit()
        
        # Act
        query = """
            query GetPosts($page: Int!, $limit: Int!) {
                posts(page: $page, limit: $limit) {
                    edges {
                        node {
                            id
                            title
                            status
                        }
                    }
                    pageInfo {
                        totalCount
                    }
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"page": 1, "limit": 10}
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        
        posts_data = data["data"]["posts"]
        assert posts_data["pageInfo"]["totalCount"] == 3
        
        # 檢查只返回已發布的文章
        for edge in posts_data["edges"]:
            assert edge["node"]["status"] == "PUBLISHED"
            assert "已發布" in edge["node"]["title"]
    
    @pytest.mark.asyncio
    async def test_posts_ordered_by_created_at(
        self,
        client,
        test_session
    ):
        """測試：文章按創建時間排序（最新的在前）"""
        # Arrange
        user = await UserFactory.create(test_session)
        
        # 建立不同時間的文章
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="較舊的文章",
            status=PostStatus.PUBLISHED
        )
        
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="較新的文章",
            status=PostStatus.PUBLISHED
        )
        
        await test_session.commit()
        
        # Act
        query = """
            query GetPosts($page: Int!, $limit: Int!) {
                posts(page: $page, limit: $limit) {
                    edges {
                        node {
                            id
                            title
                        }
                    }
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"page": 1, "limit": 10}
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        posts = data["data"]["posts"]["edges"]
        assert len(posts) == 2
        assert posts[0]["node"]["title"] == "較新的文章"
        assert posts[1]["node"]["title"] == "較舊的文章"
    
    @pytest.mark.asyncio
    async def test_posts_empty_list(
        self,
        client
    ):
        """測試：沒有文章時返回空列表"""
        # Act
        query = """
            query GetPosts($page: Int!, $limit: Int!) {
                posts(page: $page, limit: $limit) {
                    edges {
                        node {
                            id
                        }
                    }
                    pageInfo {
                        totalCount
                        hasNextPage
                    }
                }
            }
        """
        
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"page": 1, "limit": 10}
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        
        posts_data = data["data"]["posts"]
        assert len(posts_data["edges"]) == 0
        assert posts_data["pageInfo"]["totalCount"] == 0
        assert posts_data["pageInfo"]["hasNextPage"] is False