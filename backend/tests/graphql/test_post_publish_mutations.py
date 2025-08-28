import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.post import Post, PostStatus
from app.services.auth import AuthService


class TestPublishPostMutation:
    """測試發布文章 mutation"""

    @pytest.mark.asyncio
    async def test_publish_post_success(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試成功發布文章"""
        # 創建測試文章
        post = Post(
            title="Test Post",
            slug="test-post",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.DRAFT
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 生成認證 token
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 publishPost mutation
        mutation = """
            mutation PublishPost($id: ID!) {
                publishPost(id: $id) {
                    id
                    title
                    status
                    publishedAt
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證結果
        assert "data" in data
        assert "publishPost" in data["data"]
        result = data["data"]["publishPost"]

        assert str(result["id"]) == str(post.id)
        assert result["status"] == "PUBLISHED"
        assert result["publishedAt"] is not None

        # 驗證資料庫中的文章狀態
        await test_session.refresh(post)
        assert post.status == PostStatus.PUBLISHED
        assert post.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_post_already_published(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試重複發布已發布的文章"""
        # 創建已發布的文章
        published_at = datetime.now(timezone.utc)
        post = Post(
            title="Published Post",
            slug="published-post",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.PUBLISHED,
            published_at=published_at
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 生成認證 token
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 publishPost mutation
        mutation = """
            mutation PublishPost($id: ID!) {
                publishPost(id: $id) {
                    id
                    status
                    publishedAt
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回錯誤
        assert "errors" in data
        assert "already published" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_publish_post_not_author(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試非作者無法發布文章"""
        # 創建另一個用戶作為作者
        author = User(
            email="author@example.com",
            username="author",
            hashed_password="hashed"
        )
        test_session.add(author)
        await test_session.commit()
        await test_session.refresh(author)

        # 創建文章（作者是 author，不是 test_user）
        post = Post(
            title="Author's Post",
            slug="authors-post",
            content="Test content",
            author_id=author.id,
            status=PostStatus.DRAFT
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 以 test_user 身份嘗試發布
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 publishPost mutation
        mutation = """
            mutation PublishPost($id: ID!) {
                publishPost(id: $id) {
                    id
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回權限錯誤
        assert "errors" in data
        assert "permission" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_publish_post_not_authenticated(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試未登入用戶無法發布文章"""
        # 創建文章
        post = Post(
            title="Test Post",
            slug="test-post-unauth",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.DRAFT
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 執行 publishPost mutation（不帶認證 header）
        mutation = """
            mutation PublishPost($id: ID!) {
                publishPost(id: $id) {
                    id
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回認證錯誤
        assert "errors" in data
        assert "authentication" in str(data["errors"][0]["message"]).lower() or "authenticated" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_publish_deleted_post(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試無法發布已刪除的文章"""
        # 創建已刪除的文章
        post = Post(
            title="Deleted Post",
            slug="deleted-post",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.DRAFT,
            deleted_at=datetime.now(timezone.utc)
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 生成認證 token
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 publishPost mutation
        mutation = """
            mutation PublishPost($id: ID!) {
                publishPost(id: $id) {
                    id
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回找不到文章的錯誤
        assert "errors" in data
        assert "not found" in str(data["errors"][0]["message"]).lower()


class TestUnpublishPostMutation:
    """測試取消發布文章 mutation"""

    @pytest.mark.asyncio
    async def test_unpublish_post_success(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試成功取消發布文章"""
        # 創建已發布的文章
        post = Post(
            title="Published Post",
            slug="published-post-unpub",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(timezone.utc)
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 生成認證 token
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 unpublishPost mutation
        mutation = """
            mutation UnpublishPost($id: ID!) {
                unpublishPost(id: $id) {
                    id
                    title
                    status
                    publishedAt
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證結果
        assert "data" in data
        assert "unpublishPost" in data["data"]
        result = data["data"]["unpublishPost"]

        assert str(result["id"]) == str(post.id)
        assert result["status"] == "DRAFT"
        assert result["publishedAt"] is None

        # 驗證資料庫中的文章狀態
        await test_session.refresh(post)
        assert post.status == PostStatus.DRAFT
        assert post.published_at is None

    @pytest.mark.asyncio
    async def test_unpublish_draft_post(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試取消發布草稿文章"""
        # 創建草稿文章
        post = Post(
            title="Draft Post",
            slug="draft-post-unpub",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.DRAFT
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 生成認證 token
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 unpublishPost mutation
        mutation = """
            mutation UnpublishPost($id: ID!) {
                unpublishPost(id: $id) {
                    id
                    status
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回錯誤
        assert "errors" in data
        assert "not published" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_unpublish_post_not_author(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試非作者無法取消發布文章"""
        # 創建另一個用戶作為作者
        author = User(
            email="author2@example.com",
            username="author2",
            hashed_password="hashed"
        )
        test_session.add(author)
        await test_session.commit()
        await test_session.refresh(author)

        # 創建已發布的文章
        post = Post(
            title="Author's Published Post",
            slug="authors-published-post",
            content="Test content",
            author_id=author.id,
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(timezone.utc)
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 以 test_user 身份嘗試取消發布
        access_token = AuthService.create_access_token(
            data={"sub": str(test_user.id)}
        )

        # 執行 unpublishPost mutation
        mutation = """
            mutation UnpublishPost($id: ID!) {
                unpublishPost(id: $id) {
                    id
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回權限錯誤
        assert "errors" in data
        assert "permission" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_unpublish_post_not_authenticated(self, client: AsyncClient, test_session: AsyncSession, test_user: User):
        """測試未登入用戶無法取消發布文章"""
        # 創建已發布的文章
        post = Post(
            title="Published Post",
            slug="published-post-unauth",
            content="Test content",
            author_id=test_user.id,
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(timezone.utc)
        )
        test_session.add(post)
        await test_session.commit()
        await test_session.refresh(post)

        # 執行 unpublishPost mutation（不帶認證 header）
        mutation = """
            mutation UnpublishPost($id: ID!) {
                unpublishPost(id: $id) {
                    id
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": str(post.id)}}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回認證錯誤
        assert "errors" in data
        assert "authentication" in str(data["errors"][0]["message"]).lower() or "authenticated" in str(data["errors"][0]["message"]).lower()