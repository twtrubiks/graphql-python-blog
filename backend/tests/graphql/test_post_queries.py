import pytest
from tests.factories import UserFactory, PostFactory
from app.models.post import PostStatus
from app.core.security import create_access_token


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


class TestPostQueryBySlug:
    """測試通過 slug 查詢文章"""

    @pytest.mark.asyncio
    async def test_get_post_by_slug_success(
        self,
        client,
        test_session
    ):
        """測試：成功通過 slug 查詢文章"""
        # Arrange
        user = await UserFactory.create(test_session)
        post = await PostFactory.create(
            test_session,
            author_id=user.id,
            title="測試文章",
            slug="test-article",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act - 使用 slug 參數查詢
        query = """
            query GetPostBySlug($slug: String!) {
                post(slug: $slug) {
                    id
                    title
                    slug
                    status
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"slug": "test-article"}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        post_data = data["data"]["post"]
        assert str(post_data["id"]) == str(post.id)
        assert post_data["title"] == "測試文章"
        assert post_data["slug"] == "test-article"
        assert post_data["status"] == "PUBLISHED"

    @pytest.mark.asyncio
    async def test_get_post_auto_detect_slug(
        self,
        client,
        test_session
    ):
        """測試：自動判斷 ID 參數為 slug"""
        # Arrange
        user = await UserFactory.create(test_session)
        post = await PostFactory.create(
            test_session,
            author_id=user.id,
            title="自動判斷測試",
            slug="auto-detect-test",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act - 使用 id 參數但傳入 slug 值
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                    slug
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": "auto-detect-test"}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        post_data = data["data"]["post"]
        assert str(post_data["id"]) == str(post.id)
        assert post_data["slug"] == "auto-detect-test"

    @pytest.mark.asyncio
    async def test_get_post_by_slug_not_found(
        self,
        client
    ):
        """測試：查詢不存在的 slug"""
        query = """
            query GetPostBySlug($slug: String!) {
                post(slug: $slug) {
                    id
                    title
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"slug": "non-existent-slug"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["post"] is None

    @pytest.mark.asyncio
    async def test_get_draft_post_by_slug_with_permission(
        self,
        client,
        test_session
    ):
        """測試：作者可以通過 slug 查看自己的草稿"""
        # Arrange
        user = await UserFactory.create(test_session)
        post = await PostFactory.create(
            test_session,
            author_id=user.id,
            title="草稿測試",
            slug="draft-test",
            status=PostStatus.DRAFT
        )
        await test_session.commit()

        # 使用作者的認證
        access_token = create_access_token(data={"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {access_token}"}

        # Act
        query = """
            query GetPostBySlug($slug: String!) {
                post(slug: $slug) {
                    id
                    title
                    slug
                    status
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"slug": "draft-test"}
            },
            headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        post_data = data["data"]["post"]
        assert str(post_data["id"]) == str(post.id)
        assert post_data["slug"] == "draft-test"
        assert post_data["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_cannot_get_others_draft_by_slug(
        self,
        client,
        test_session
    ):
        """測試：無法通過 slug 查看他人的草稿"""
        # Arrange
        author = await UserFactory.create(test_session)
        other_user = await UserFactory.create(test_session)

        post = await PostFactory.create(
            test_session,
            author_id=author.id,
            title="他人草稿",
            slug="others-draft",
            status=PostStatus.DRAFT
        )
        await test_session.commit()

        # 使用其他用戶的認證
        access_token = create_access_token(data={"sub": str(other_user.id)})
        headers = {"Authorization": f"Bearer {access_token}"}

        # Act
        query = """
            query GetPostBySlug($slug: String!) {
                post(slug: $slug) {
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
                "variables": {"slug": "others-draft"}
            },
            headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["post"] is None

    @pytest.mark.asyncio
    async def test_mixed_id_and_slug_query(
        self,
        client,
        test_session
    ):
        """測試：同時支援數字 ID 和 slug 查詢"""
        # Arrange
        user = await UserFactory.create(test_session)
        post = await PostFactory.create(
            test_session,
            author_id=user.id,
            title="混合測試",
            slug="mixed-test",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act 1 - 使用數字 ID 查詢
        query = """
            query GetPost($id: ID!) {
                post(id: $id) {
                    id
                    title
                    slug
                }
            }
        """

        response1 = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(post.id)}
            }
        )

        # Act 2 - 使用 slug 查詢
        response2 = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": "mixed-test"}
            }
        )

        # Assert - 兩種方式都應該返回相同的文章
        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert data1["data"]["post"]["id"] == data2["data"]["post"]["id"]
        assert data1["data"]["post"]["slug"] == "mixed-test"
        assert data2["data"]["post"]["slug"] == "mixed-test"