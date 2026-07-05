"""GraphQL 查詢限制測試

驗證公開端點的 DoS 防護：
1. 查詢深度限制 - 防止 user -> followers -> following -> ... 無限巢狀放大
2. 分頁 limit 上限 - 防止單次查詢撈取過多資料
3. 非法分頁參數（0 或負數）不會造成伺服器錯誤
"""

import pytest

from tests.factories import UserFactory, PostFactory


def _nested_users_query(depth: int) -> str:
    """產生指定巢狀深度的 followers/following 查詢"""
    inner = "id"
    for i in range(depth):
        field = "followers" if i % 2 == 0 else "following"
        inner = f"{field} {{ {inner} }}"
    return f"query {{ users {{ {inner} }} }}"


class TestQueryDepthLimit:
    """查詢深度限制測試"""

    @pytest.mark.asyncio
    async def test_deeply_nested_query_is_rejected(self, client):
        """超過深度限制的巢狀查詢應被拒絕"""
        query = _nested_users_query(15)

        response = await client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert any("depth" in err["message"].lower() for err in data["errors"])

    @pytest.mark.asyncio
    async def test_normal_query_is_allowed(self, client, test_session):
        """一般深度的查詢（如前端實際使用的查詢）應正常執行"""
        user = await UserFactory.create(test_session)
        await PostFactory.create(test_session, author_id=user.id)
        await test_session.commit()

        query = """
            query {
                posts(page: 1, limit: 10) {
                    edges {
                        node {
                            id
                            title
                            author {
                                username
                                followersCount
                            }
                        }
                    }
                    pageInfo {
                        totalCount
                    }
                }
            }
        """

        response = await client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert len(data["data"]["posts"]["edges"]) == 1


class TestPaginationLimit:
    """分頁參數上限測試"""

    @pytest.mark.asyncio
    async def test_posts_limit_is_clamped_to_max(self, client, test_session):
        """limit 超過上限時應被鉗制為最大值（50）"""
        user = await UserFactory.create(test_session)
        for _ in range(55):
            await PostFactory.create(test_session, author_id=user.id)
        await test_session.commit()

        query = """
            query {
                posts(page: 1, limit: 500) {
                    edges { node { id } }
                    pageInfo { totalCount }
                }
            }
        """

        response = await client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert len(data["data"]["posts"]["edges"]) == 50
        assert data["data"]["posts"]["pageInfo"]["totalCount"] == 55

    @pytest.mark.asyncio
    async def test_posts_invalid_pagination_params_are_safe(self, client, test_session):
        """limit=0 或 page=0 不應造成伺服器錯誤（除以零 / 負數 offset）"""
        user = await UserFactory.create(test_session)
        await PostFactory.create(test_session, author_id=user.id)
        await test_session.commit()

        query = """
            query {
                posts(page: 0, limit: 0) {
                    edges { node { id } }
                    pageInfo { currentPage }
                }
            }
        """

        response = await client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert len(data["data"]["posts"]["edges"]) == 1
        assert data["data"]["posts"]["pageInfo"]["currentPage"] == 1

    @pytest.mark.asyncio
    async def test_users_limit_is_clamped(self, client, test_session):
        """users 查詢的 limit 也應被鉗制，不允許無上限撈取"""
        await UserFactory.create(test_session)
        await test_session.commit()

        query = """
            query {
                users(page: 1, limit: 10000) {
                    id
                }
            }
        """

        response = await client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert len(data["data"]["users"]) <= 50
