"""Test post search functionality

測試文章搜尋功能，包括：
- 按標題搜尋
- 按內容搜尋
- 搜尋結果分頁
- 無結果情況
"""

import pytest
from tests.factories import UserFactory, PostFactory
from app.models.post import PostStatus


class TestPostSearch:
    """測試文章搜尋功能"""

    @pytest.mark.asyncio
    async def test_search_posts_by_title(self, client, test_session):
        """測試：按標題搜尋文章"""
        # Arrange - 創建測試數據
        user = await UserFactory.create(test_session)

        # 創建多篇文章，部分包含搜尋關鍵字
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="GraphQL 入門教學",
            content="這是一篇關於 API 的文章",
            status=PostStatus.PUBLISHED
        )
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="Python 基礎",
            content="Python 程式語言教學",
            status=PostStatus.PUBLISHED
        )
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="進階 GraphQL 技巧",
            content="深入了解 GraphQL",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act - 執行 GraphQL 查詢
        query = """
            query SearchPosts($search: String) {
                posts(search: $search) {
                    edges {
                        node {
                            id
                            title
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
            json={"query": query, "variables": {"search": "GraphQL"}}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        posts = data["data"]["posts"]
        assert posts["pageInfo"]["totalCount"] == 2

        titles = [edge["node"]["title"] for edge in posts["edges"]]
        assert "GraphQL 入門教學" in titles
        assert "進階 GraphQL 技巧" in titles
        assert "Python 基礎" not in titles

    @pytest.mark.asyncio
    async def test_search_posts_by_content(self, client, test_session):
        """測試：按內容搜尋文章"""
        # Arrange
        user = await UserFactory.create(test_session)

        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="文章一",
            content="這篇文章討論 WebSocket 實時通訊",
            status=PostStatus.PUBLISHED
        )
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="文章二",
            content="REST API 設計模式",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act
        query = """
            query SearchPosts($search: String) {
                posts(search: $search) {
                    edges {
                        node {
                            id
                            title
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
            json={"query": query, "variables": {"search": "WebSocket"}}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        posts = data["data"]["posts"]
        assert posts["pageInfo"]["totalCount"] == 1
        assert posts["edges"][0]["node"]["title"] == "文章一"

    @pytest.mark.asyncio
    async def test_search_posts_case_insensitive(self, client, test_session):
        """測試：搜尋不區分大小寫"""
        # Arrange
        user = await UserFactory.create(test_session)

        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="DOCKER 容器化部署",
            content="使用 Docker 進行部署",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act - 使用小寫搜尋
        query = """
            query SearchPosts($search: String) {
                posts(search: $search) {
                    edges {
                        node {
                            title
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
            json={"query": query, "variables": {"search": "docker"}}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["posts"]["pageInfo"]["totalCount"] == 1

    @pytest.mark.asyncio
    async def test_search_posts_no_results(self, client, test_session):
        """測試：搜尋無結果"""
        # Arrange
        user = await UserFactory.create(test_session)

        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="Python 教學",
            content="Python 入門",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act
        query = """
            query SearchPosts($search: String) {
                posts(search: $search) {
                    edges {
                        node {
                            title
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
            json={"query": query, "variables": {"search": "不存在的關鍵字"}}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["posts"]["pageInfo"]["totalCount"] == 0
        assert len(data["data"]["posts"]["edges"]) == 0

    @pytest.mark.asyncio
    async def test_search_posts_with_pagination(self, client, test_session):
        """測試：搜尋結果分頁"""
        # Arrange
        user = await UserFactory.create(test_session)

        # 創建 5 篇包含 "測試" 的文章
        for i in range(5):
            await PostFactory.create(
                test_session,
                author_id=user.id,
                title=f"測試文章 {i+1}",
                content=f"測試內容 {i+1}",
                status=PostStatus.PUBLISHED
            )
        await test_session.commit()

        # Act - 搜尋並限制每頁 2 篇
        query = """
            query SearchPosts($search: String, $page: Int, $limit: Int) {
                posts(search: $search, page: $page, limit: $limit) {
                    edges {
                        node {
                            title
                        }
                    }
                    pageInfo {
                        totalCount
                        totalPages
                        currentPage
                        hasNextPage
                        hasPreviousPage
                    }
                }
            }
        """
        response = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"search": "測試", "page": 1, "limit": 2}
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        posts = data["data"]["posts"]
        assert posts["pageInfo"]["totalCount"] == 5
        assert posts["pageInfo"]["totalPages"] == 3
        assert posts["pageInfo"]["currentPage"] == 1
        assert posts["pageInfo"]["hasNextPage"] is True
        assert posts["pageInfo"]["hasPreviousPage"] is False
        assert len(posts["edges"]) == 2

    @pytest.mark.asyncio
    async def test_search_posts_empty_string(self, client, test_session):
        """測試：空字串搜尋返回所有文章"""
        # Arrange
        user = await UserFactory.create(test_session)

        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="文章一",
            status=PostStatus.PUBLISHED
        )
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="文章二",
            status=PostStatus.PUBLISHED
        )
        await test_session.commit()

        # Act - 空字串搜尋
        query = """
            query SearchPosts($search: String) {
                posts(search: $search) {
                    pageInfo {
                        totalCount
                    }
                }
            }
        """
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"search": ""}}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        # 空字串應該返回所有文章
        assert data["data"]["posts"]["pageInfo"]["totalCount"] == 2

    @pytest.mark.asyncio
    async def test_search_posts_only_published(self, client, test_session):
        """測試：搜尋只返回已發布的文章"""
        # Arrange
        user = await UserFactory.create(test_session)

        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="已發布的 GraphQL 教學",
            status=PostStatus.PUBLISHED
        )
        await PostFactory.create(
            test_session,
            author_id=user.id,
            title="草稿 GraphQL 筆記",
            status=PostStatus.DRAFT
        )
        await test_session.commit()

        # Act
        query = """
            query SearchPosts($search: String) {
                posts(search: $search) {
                    edges {
                        node {
                            title
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
            json={"query": query, "variables": {"search": "GraphQL"}}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        # 只應該返回已發布的文章
        posts = data["data"]["posts"]
        assert posts["pageInfo"]["totalCount"] == 1
        assert posts["edges"][0]["node"]["title"] == "已發布的 GraphQL 教學"
