"""updateMe mutation 測試（個人資料編輯）"""
import pytest
from httpx import AsyncClient


UPDATE_ME_MUTATION = """
mutation UpdateMe($input: UpdateUserInput!) {
    updateMe(input: $input) {
        id
        username
        fullName
        bio
        avatarUrl
    }
}
"""

ME_QUERY = "query { me { username fullName bio avatarUrl } }"


async def update_me(client: AsyncClient, **fields) -> dict:
    response = await client.post(
        "/graphql",
        json={"query": UPDATE_ME_MUTATION, "variables": {"input": fields}}
    )
    assert response.status_code == 200
    return response.json()


async def query_me(client: AsyncClient) -> dict:
    """用新的請求查詢，確認資料真的寫進資料庫"""
    response = await client.post("/graphql", json={"query": ME_QUERY})
    return response.json()["data"]["me"]


def error_message(data: dict) -> str:
    assert data["data"] is None
    return data["errors"][0]["message"]


@pytest.mark.asyncio
class TestUpdateMe:
    async def test_update_profile_fields(self, authenticated_client: AsyncClient, test_user):
        """更新姓名、簡介、頭像，前後空白會被去除"""
        data = await update_me(
            authenticated_client,
            fullName="  Test User  ",
            bio="  Hello there  ",
            avatarUrl="  https://example.com/avatar.png  ",
        )

        assert "errors" not in data
        expected = {
            "username": "testuser",
            "fullName": "Test User",
            "bio": "Hello there",
            "avatarUrl": "https://example.com/avatar.png",
        }
        assert data["data"]["updateMe"] == {"id": str(test_user.id), **expected}
        assert await query_me(authenticated_client) == expected

    async def test_partial_update_keeps_other_fields(self, authenticated_client: AsyncClient):
        """只送部分欄位時，其他欄位保持不變"""
        await update_me(authenticated_client, fullName="Original Name", bio="Original bio")

        data = await update_me(authenticated_client, bio="New bio")

        assert "errors" not in data
        assert await query_me(authenticated_client) == {
            "username": "testuser",
            "fullName": "Original Name",
            "bio": "New bio",
            "avatarUrl": None,
        }

    async def test_empty_strings_clear_fields(self, authenticated_client: AsyncClient):
        """送空字串代表清除欄位"""
        await update_me(
            authenticated_client,
            fullName="Name",
            bio="Bio",
            avatarUrl="https://example.com/a.png",
        )

        data = await update_me(authenticated_client, fullName="", bio="", avatarUrl="")

        assert "errors" not in data
        assert await query_me(authenticated_client) == {
            "username": "testuser",
            "fullName": None,
            "bio": None,
            "avatarUrl": None,
        }

    async def test_change_username(self, authenticated_client: AsyncClient):
        data = await update_me(authenticated_client, username="  newname  ")

        assert "errors" not in data
        assert data["data"]["updateMe"]["username"] == "newname"
        assert (await query_me(authenticated_client))["username"] == "newname"

    async def test_keep_own_username(self, authenticated_client: AsyncClient):
        """送出自己目前的 username 不算重複"""
        data = await update_me(authenticated_client, username="testuser", bio="still me")

        assert "errors" not in data
        assert data["data"]["updateMe"]["username"] == "testuser"
        assert data["data"]["updateMe"]["bio"] == "still me"

    async def test_empty_username_is_ignored(self, authenticated_client: AsyncClient):
        """空字串的 username 視為沒有要修改"""
        data = await update_me(authenticated_client, username="")

        assert "errors" not in data
        assert data["data"]["updateMe"]["username"] == "testuser"

    async def test_blank_username_rejected(self, authenticated_client: AsyncClient):
        data = await update_me(authenticated_client, username="   ")

        assert error_message(data) == "Username cannot be empty"
        assert (await query_me(authenticated_client))["username"] == "testuser"

    async def test_username_taken(self, authenticated_client: AsyncClient, user_factory):
        await user_factory.create(username="taken")

        data = await update_me(authenticated_client, username="taken")

        assert error_message(data) == "Username already taken"
        assert (await query_me(authenticated_client))["username"] == "testuser"

    async def test_username_taken_with_surrounding_spaces(self, authenticated_client: AsyncClient, user_factory):
        """前後有空白的重複名稱也要被擋下，而不是撞上資料庫的 unique 限制"""
        await user_factory.create(username="taken")

        data = await update_me(authenticated_client, username="  taken  ")

        assert error_message(data) == "Username already taken"

    async def test_bio_at_max_length(self, authenticated_client: AsyncClient):
        bio = "字" * 200

        data = await update_me(authenticated_client, bio=bio)

        assert "errors" not in data
        assert data["data"]["updateMe"]["bio"] == bio

    async def test_bio_too_long(self, authenticated_client: AsyncClient):
        data = await update_me(authenticated_client, bio="字" * 201)

        assert error_message(data) == "個人簡介不能超過 200 字"

    @pytest.mark.parametrize("url", ["not-a-url", "javascript:alert(1)", "ftp://example.com/a.png"])
    async def test_invalid_avatar_url(self, authenticated_client: AsyncClient, url):
        data = await update_me(authenticated_client, avatarUrl=url)

        assert error_message(data) == "請輸入有效的圖片網址"

    async def test_failed_update_does_not_save_other_fields(self, authenticated_client: AsyncClient):
        """驗證失敗時，同一次請求中其他欄位的變更也不能寫入"""
        data = await update_me(authenticated_client, fullName="Should Not Save", bio="字" * 201)

        assert error_message(data) == "個人簡介不能超過 200 字"
        assert (await query_me(authenticated_client))["fullName"] is None

    async def test_requires_authentication(self, client: AsyncClient):
        data = await update_me(client, fullName="Anonymous")

        assert error_message(data) == "Authentication required"
