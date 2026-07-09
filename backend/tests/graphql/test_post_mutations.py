"""
🎓 教學重點：TDD (Test-Driven Development) 實踐範例

這個測試檔案展示如何使用 TDD 方法開發 GraphQL Mutation：

## TDD 三步驟循環（紅燈-綠燈-重構）
1. 🔴 Red: 先寫測試（會失敗）
2. 🟢 Green: 實作最簡單的程式碼讓測試通過
3. 🔵 Refactor: 重構程式碼保持品質

## 學習建議
1. 從 test_create_post_success 開始，了解基本的 Mutation 測試
2. 觀察如何測試錯誤情況（authentication, validation）
3. 注意權限控制的測試（owner vs non-owner）
4. 軟刪除機制的測試設計

## 相關文件
- docs/tdd-guide.md - 完整 TDD 指南
- docs/graphql-examples.md - GraphQL 查詢範例
"""
import pytest
from sqlalchemy import select

from app.models.post import Post


class TestCreatePostMutation:
    """
    測試 createPost mutation

    🎯 TDD 開發流程示範：
    假設我們要開發「建立文章」功能，TDD 步驟如下：

    第一步（🔴 Red）：
        1. 寫這個測試 test_create_post_success（會失敗）
        2. 執行：pytest tests/graphql/test_post_mutations.py::TestCreatePostMutation::test_create_post_success
        3. 看到錯誤：createPost mutation 不存在

    第二步（🟢 Green）：
        1. 實作 app/graphql/mutations/post.py 中的 createPost
        2. 實作最簡單的版本（只要能通過測試）
        3. 執行測試，確認通過

    第三步（🔵 Refactor）：
        1. 重構程式碼（改善結構、效能）
        2. 確保測試仍然通過
        3. 完成！
    """

    @pytest.mark.asyncio
    async def test_create_post_success(self, authenticated_client, test_session):
        """
        測試：成功建立文章（需要認證）

        📝 測試設計說明：
        - 使用 authenticated_client（已登入的使用者）
        - 測試完整的 GraphQL Mutation 流程
        - 驗證返回資料的完整性
        - 檢查自動生成的欄位（如 slug, timestamps）

        💡 TDD 提示：
        這是最基本的「Happy Path」測試，應該最先實作。
        通過這個測試後，再逐步加上錯誤處理的測試。
        """

        # ==================== Arrange（準備）====================
        # 📝 定義 GraphQL mutation 查詢
        # 注意事項：
        # 1. 使用變數 ($input) 而不是硬編碼值（安全性 + 重用性）
        # 2. 明確指定需要的欄位（GraphQL 特色：按需取得）
        # 3. 包含 author 子查詢（測試關聯資料）
        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                slug
                content
                excerpt
                status
                author {
                    id
                    username
                }
                createdAt
                updatedAt
            }
        }
        """

        # 📝 準備測試資料
        # TDD 提示：使用有意義的測試資料，方便 debug
        variables = {
            "input": {
                "title": "My First Blog Post",
                "content": "This is the content of my first blog post. It's quite interesting!",
                "excerpt": "A brief excerpt of my post",
                "status": "DRAFT"
            }
        }

        # ==================== Act（執行）====================
        # 📝 發送 GraphQL 請求
        # 注意：使用 authenticated_client（模擬已登入使用者）
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        # ==================== Assert（驗證）====================
        # 📝 Step 1: 驗證 HTTP 狀態碼
        assert response.status_code == 200
        data = response.json()

        # 📝 Step 2: 確認沒有 GraphQL 錯誤
        assert "errors" not in data

        # 📝 Step 3: 驗證返回的業務資料
        assert data["data"]["createPost"]["title"] == "My First Blog Post"
        assert data["data"]["createPost"]["content"] == "This is the content of my first blog post. It's quite interesting!"
        assert data["data"]["createPost"]["excerpt"] == "A brief excerpt of my post"
        assert data["data"]["createPost"]["status"] == "DRAFT"
        assert data["data"]["createPost"]["slug"] == "my-first-blog-post"  # 自動生成的 slug
        assert data["data"]["createPost"]["author"]["username"] is not None
        assert data["data"]["createPost"]["createdAt"] is not None
        assert data["data"]["createPost"]["updatedAt"] is not None

    @pytest.mark.asyncio
    async def test_create_post_without_auth(self, client):
        """測試：未認證用戶無法建立文章"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        # 測試資料
        variables = {
            "input": {
                "title": "Unauthorized Post",
                "content": "This should not be created",
            }
        }

        # 發送請求（未認證的客戶端）
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回認證錯誤
        assert "errors" in data
        assert "Authentication required" in str(data["errors"][0]["message"])

    @pytest.mark.asyncio
    async def test_create_post_auto_slug_generation(self, authenticated_client, test_session):
        """測試：自動生成 slug（從標題轉換）"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                slug
            }
        }
        """

        # 測試各種標題格式的 slug 生成
        test_cases = [
            ("Simple Title", "simple-title"),  # 簡單英文標題
            ("Title with Numbers 123", "title-with-numbers-123"),  # 包含數字
            ("  Spaces  Around  ", "spaces-around"),  # 前後有空格
            ("Special!@#$%^&*()Characters", "special-characters"),  # 特殊字元
            ("中文標題", "zhong-wen-biao-ti"),  # 中文會轉換為拼音
        ]

        for title, expected_slug_base in test_cases:
            variables = {
                "input": {
                    "title": title,
                    "content": "Test content for slug generation",
                }
            }

            response = await authenticated_client.post(
                "/graphql",
                json={"query": mutation, "variables": variables}
            )

            assert response.status_code == 200
            data = response.json()

            assert "errors" not in data
            assert data["data"]["createPost"]["title"] == title.strip()
            # Slug 應該以預期的基礎開頭（可能會附加數字以確保唯一性）
            assert data["data"]["createPost"]["slug"].startswith(expected_slug_base.lower())

    @pytest.mark.asyncio
    async def test_create_post_unique_slug(self, authenticated_client, test_session):
        """測試：重複的 slug 會自動變成唯一值"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                slug
            }
        }
        """

        # 建立第一篇文章
        variables = {
            "input": {
                "title": "Duplicate Title",
                "content": "First post with this title",
            }
        }

        response1 = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["data"]["createPost"]["slug"] == "duplicate-title"

        # 建立第二篇相同標題的文章
        response2 = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response2.status_code == 200
        data2 = response2.json()
        # 第二篇文章應該有唯一的 slug（會自動加上數字）
        assert data2["data"]["createPost"]["slug"] != "duplicate-title"
        assert data2["data"]["createPost"]["slug"].startswith("duplicate-title-")

    @pytest.mark.asyncio
    async def test_create_post_with_custom_slug(self, authenticated_client, test_session):
        """測試：使用自訂 slug 建立文章"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                slug
            }
        }
        """

        variables = {
            "input": {
                "title": "Post with Custom Slug",
                "content": "This post has a custom slug",
                "slug": "my-custom-slug"
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()

        assert "errors" not in data
        assert data["data"]["createPost"]["slug"] == "my-custom-slug"

    @pytest.mark.asyncio
    async def test_create_post_draft_status_default(self, authenticated_client, test_session):
        """測試：文章預設狀態為草稿（DRAFT）"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                status
                publishedAt
            }
        }
        """

        variables = {
            "input": {
                "title": "Default Status Post",
                "content": "Testing default status",
                # 不指定 status - 應該預設為 DRAFT
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()

        assert "errors" not in data
        assert data["data"]["createPost"]["status"] == "DRAFT"
        assert data["data"]["createPost"]["publishedAt"] is None  # 草稿沒有發布時間

    @pytest.mark.asyncio
    async def test_create_post_published_status(self, authenticated_client, test_session):
        """測試：建立已發布文章會設定 publishedAt 時間"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                status
                publishedAt
            }
        }
        """

        variables = {
            "input": {
                "title": "Published Post",
                "content": "This post is published immediately",
                "status": "PUBLISHED"
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()

        assert "errors" not in data
        assert data["data"]["createPost"]["status"] == "PUBLISHED"
        assert data["data"]["createPost"]["publishedAt"] is not None  # 已發布文章有發布時間

    @pytest.mark.asyncio
    async def test_create_post_validation_errors(self, authenticated_client, test_session):
        """測試：輸入驗證錯誤處理"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        # 測試空標題
        variables = {
            "input": {
                "title": "",
                "content": "Content without title",
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data  # 應該有錯誤

        # 測試空內容
        variables = {
            "input": {
                "title": "Title without content",
                "content": "",
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data  # 應該有錯誤

    @pytest.mark.asyncio
    async def test_create_post_with_all_fields(self, authenticated_client, test_session):
        """測試：使用所有欄位建立文章"""

        mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                slug
                content
                excerpt
                status
            }
        }
        """

        # 提供所有可選欄位的測試資料
        variables = {
            "input": {
                "title": "Complete Post",
                "content": "This is a complete post with all fields specified.",
                "excerpt": "A complete post",
                "slug": "complete-post",  # 自訂 slug
                "status": "DRAFT"
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證所有欄位都正確設定
        assert "errors" not in data
        assert data["data"]["createPost"]["title"] == "Complete Post"
        assert data["data"]["createPost"]["slug"] == "complete-post"
        assert data["data"]["createPost"]["content"] == "This is a complete post with all fields specified."
        assert data["data"]["createPost"]["excerpt"] == "A complete post"
        assert data["data"]["createPost"]["status"] == "DRAFT"


class TestUpdatePostMutation:
    """測試 updatePost mutation"""

    @pytest.mark.asyncio
    async def test_update_post_by_author(self, authenticated_client, test_session, test_user):
        """測試：作者可以更新自己的文章"""
        # 先建立一篇文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                content
            }
        }
        """

        create_variables = {
            "input": {
                "title": "Original Title",
                "content": "Original content"
            }
        }

        create_response = await authenticated_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables}
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        post_id = create_data["data"]["createPost"]["id"]

        # 更新文章
        update_mutation = """
        mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
            updatePost(id: $id, input: $input) {
                id
                title
                content
                slug
                excerpt
                status
                updatedAt
            }
        }
        """

        update_variables = {
            "id": post_id,
            "input": {
                "title": "Updated Title",
                "content": "Updated content with more details",
                "excerpt": "Updated excerpt",
                "status": "PUBLISHED"
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證更新成功
        assert "errors" not in data
        assert data["data"]["updatePost"]["id"] == post_id
        assert data["data"]["updatePost"]["title"] == "Updated Title"
        assert data["data"]["updatePost"]["content"] == "Updated content with more details"
        assert data["data"]["updatePost"]["excerpt"] == "Updated excerpt"
        assert data["data"]["updatePost"]["status"] == "PUBLISHED"
        assert data["data"]["updatePost"]["updatedAt"] is not None

    @pytest.mark.asyncio
    async def test_update_post_partial_fields(self, authenticated_client, test_session):
        """測試：只更新部分欄位"""

        # 先建立一篇文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
                content
                excerpt
                status
            }
        }
        """

        create_variables = {
            "input": {
                "title": "Original Title",
                "content": "Original content",
                "excerpt": "Original excerpt",
                "status": "DRAFT"
            }
        }

        create_response = await authenticated_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables}
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        post_id = create_data["data"]["createPost"]["id"]

        # 只更新標題
        update_mutation = """
        mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
            updatePost(id: $id, input: $input) {
                id
                title
                content
                excerpt
                status
            }
        }
        """

        update_variables = {
            "id": post_id,
            "input": {
                "title": "Only Title Updated"
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證只有標題被更新，其他欄位保持不變
        assert "errors" not in data
        assert data["data"]["updatePost"]["title"] == "Only Title Updated"
        assert data["data"]["updatePost"]["content"] == "Original content"
        assert data["data"]["updatePost"]["excerpt"] == "Original excerpt"
        assert data["data"]["updatePost"]["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_update_post_non_author_forbidden(self, client, test_session):
        """測試：非作者無法更新別人的文章"""
        # 註冊第一個用戶並登入
        register_mutation = """
        mutation Register($email: String!, $password: String!, $username: String!) {
            register(email: $email, password: $password, username: $username) {
                user { id }
                token
            }
        }
        """

        # 建立第一個用戶
        user1_variables = {
            "email": "author@example.com",
            "password": "Password123!",
            "username": "author"
        }

        response1 = await client.post(
            "/graphql",
            json={"query": register_mutation, "variables": user1_variables}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        author_token = data1["data"]["register"]["token"]

        # 用第一個用戶建立文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        create_variables = {
            "input": {
                "title": "Author's Post",
                "content": "This is author's content"
            }
        }

        headers1 = {"Authorization": f"Bearer {author_token}"}
        create_response = await client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables},
            headers=headers1
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        post_id = create_data["data"]["createPost"]["id"]

        # 註冊第二個用戶
        user2_variables = {
            "email": "other@example.com",
            "password": "Password123!",
            "username": "other"
        }

        response2 = await client.post(
            "/graphql",
            json={"query": register_mutation, "variables": user2_variables}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        other_token = data2["data"]["register"]["token"]

        # 第二個用戶嘗試更新第一個用戶的文章
        update_mutation = """
        mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
            updatePost(id: $id, input: $input) {
                id
                title
            }
        }
        """

        update_variables = {
            "id": post_id,
            "input": {
                "title": "Hacked Title"
            }
        }

        headers2 = {"Authorization": f"Bearer {other_token}"}
        update_response = await client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables},
            headers=headers2
        )

        assert update_response.status_code == 200
        update_data = update_response.json()

        # 應該返回權限錯誤
        assert "errors" in update_data
        assert "permission" in str(update_data["errors"][0]["message"]).lower() or \
               "authorized" in str(update_data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_update_post_not_found(self, authenticated_client):
        """測試：更新不存在的文章"""

        update_mutation = """
        mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
            updatePost(id: $id, input: $input) {
                id
                title
            }
        }
        """

        update_variables = {
            "id": "99999",  # 不存在的 ID
            "input": {
                "title": "Updated Title"
            }
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回文章不存在錯誤
        assert "errors" in data
        assert "not found" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_update_post_without_auth(self, client):
        """測試：未認證用戶無法更新文章"""

        update_mutation = """
        mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
            updatePost(id: $id, input: $input) {
                id
                title
            }
        }
        """

        update_variables = {
            "id": "1",
            "input": {
                "title": "Unauthorized Update"
            }
        }

        response = await client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回認證錯誤
        assert "errors" in data
        assert "Authentication required" in str(data["errors"][0]["message"])


class TestDeletePostMutation:
    """測試 deletePost mutation"""

    @pytest.mark.asyncio
    async def test_delete_post_by_author(self, authenticated_client, test_session):
        """測試：作者可以刪除自己的文章"""

        # 先建立一篇文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        create_variables = {
            "input": {
                "title": "Post to be deleted",
                "content": "This post will be deleted"
            }
        }

        create_response = await authenticated_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables}
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        post_id = create_data["data"]["createPost"]["id"]

        # 刪除文章
        delete_mutation = """
        mutation DeletePost($id: ID!) {
            deletePost(id: $id) {
                success
                message
            }
        }
        """

        delete_variables = {"id": post_id}

        response = await authenticated_client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證刪除成功
        assert "errors" not in data
        assert data["data"]["deletePost"]["success"] is True
        assert "deleted" in data["data"]["deletePost"]["message"].lower()

        # 驗證文章已無法查詢
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
            }
        }
        """

        query_variables = {"id": post_id}
        query_response = await authenticated_client.post(
            "/graphql",
            json={"query": query, "variables": query_variables}
        )

        assert query_response.status_code == 200
        query_data = query_response.json()
        # 文章應該不存在或返回 null
        assert query_data["data"]["post"] is None or "errors" in query_data

    @pytest.mark.asyncio
    async def test_delete_post_non_author_forbidden(self, client, test_session):
        """測試：非作者無法刪除別人的文章"""

        # 註冊第一個用戶
        register_mutation = """
        mutation Register($email: String!, $password: String!, $username: String!) {
            register(email: $email, password: $password, username: $username) {
                user { id }
                token
            }
        }
        """

        user1_variables = {
            "email": "author@example.com",
            "password": "Password123!",
            "username": "author"
        }

        response1 = await client.post(
            "/graphql",
            json={"query": register_mutation, "variables": user1_variables}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        author_token = data1["data"]["register"]["token"]

        # 用第一個用戶建立文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        create_variables = {
            "input": {
                "title": "Author's Post",
                "content": "Cannot be deleted by others"
            }
        }

        headers1 = {"Authorization": f"Bearer {author_token}"}
        create_response = await client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables},
            headers=headers1
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        post_id = create_data["data"]["createPost"]["id"]

        # 註冊第二個用戶
        user2_variables = {
            "email": "other@example.com",
            "password": "Password123!",
            "username": "other"
        }

        response2 = await client.post(
            "/graphql",
            json={"query": register_mutation, "variables": user2_variables}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        other_token = data2["data"]["register"]["token"]

        # 第二個用戶嘗試刪除第一個用戶的文章
        delete_mutation = """
        mutation DeletePost($id: ID!) {
            deletePost(id: $id) {
                success
                message
            }
        }
        """

        delete_variables = {"id": post_id}

        headers2 = {"Authorization": f"Bearer {other_token}"}
        delete_response = await client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables},
            headers=headers2
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()

        # 應該返回權限錯誤
        assert "errors" in delete_data or delete_data["data"]["deletePost"]["success"] is False
        if "errors" in delete_data:
            assert "permission" in str(delete_data["errors"][0]["message"]).lower() or \
                   "authorized" in str(delete_data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_delete_post_not_found(self, authenticated_client):
        """測試：刪除不存在的文章"""

        delete_mutation = """
        mutation DeletePost($id: ID!) {
            deletePost(id: $id) {
                success
                message
            }
        }
        """

        delete_variables = {"id": "99999"}  # 不存在的 ID

        response = await authenticated_client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回文章不存在錯誤
        assert "errors" in data or data["data"]["deletePost"]["success"] is False
        if "errors" in data:
            assert "not found" in str(data["errors"][0]["message"]).lower()

    @pytest.mark.asyncio
    async def test_delete_post_without_auth(self, client):
        """測試：未認證用戶無法刪除文章"""

        delete_mutation = """
        mutation DeletePost($id: ID!) {
            deletePost(id: $id) {
                success
                message
            }
        }
        """

        delete_variables = {"id": "1"}

        response = await client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables}
        )

        assert response.status_code == 200
        data = response.json()

        # 應該返回認證錯誤
        assert "errors" in data
        assert "Authentication required" in str(data["errors"][0]["message"])

    @pytest.mark.asyncio
    async def test_soft_delete_functionality(self, authenticated_client, test_session):
        """測試：軟刪除機制 - 文章標記為已刪除但保留在資料庫"""
        # 先建立一篇文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        create_variables = {
            "input": {
                "title": "Soft Delete Test",
                "content": "Testing soft delete mechanism"
            }
        }

        create_response = await authenticated_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables}
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        post_id = create_data["data"]["createPost"]["id"]

        # 刪除文章
        delete_mutation = """
        mutation DeletePost($id: ID!) {
            deletePost(id: $id) {
                success
                message
            }
        }
        """

        delete_variables = {"id": post_id}

        delete_response = await authenticated_client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables}
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["data"]["deletePost"]["success"] is True

        # 直接從資料庫檢查文章是否還存在但被標記為已刪除
        result = await test_session.execute(
            select(Post).where(Post.id == int(post_id))
        )
        post = result.scalar_one_or_none()

        # 軟刪除：文章應該存在但有刪除標記
        assert post is not None
        assert post.deleted_at is not None

    @pytest.mark.asyncio
    async def test_deleted_posts_not_in_list(self, authenticated_client, test_session):
        """測試：已刪除的文章不會出現在文章列表中"""

        # 建立兩篇文章
        create_mutation = """
        mutation CreatePost($input: PostInput!) {
            createPost(input: $input) {
                id
                title
            }
        }
        """

        # 第一篇文章
        create_variables1 = {
            "input": {
                "title": "Visible Post",
                "content": "This post should be visible",
                "status": "PUBLISHED"
            }
        }

        response1 = await authenticated_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables1}
        )
        assert response1.status_code == 200

        # 第二篇文章（將被刪除）
        create_variables2 = {
            "input": {
                "title": "To Be Deleted",
                "content": "This post will be deleted",
                "status": "PUBLISHED"
            }
        }

        response2 = await authenticated_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables2}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        post_id_to_delete = data2["data"]["createPost"]["id"]

        # 刪除第二篇文章
        delete_mutation = """
        mutation DeletePost($id: ID!) {
            deletePost(id: $id) {
                success
            }
        }
        """

        delete_response = await authenticated_client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": {"id": post_id_to_delete}}
        )
        assert delete_response.status_code == 200

        # 查詢文章列表
        list_query = """
        query GetPosts {
            posts(page: 1, limit: 10) {
                edges {
                    node {
                        id
                        title
                    }
                }
            }
        }
        """

        list_response = await authenticated_client.post(
            "/graphql",
            json={"query": list_query}
        )

        assert list_response.status_code == 200
        list_data = list_response.json()

        # 確認已刪除的文章不在列表中
        post_ids = [edge["node"]["id"] for edge in list_data["data"]["posts"]["edges"]]
        assert post_id_to_delete not in post_ids

        # 確認可見的文章仍在列表中
        post_titles = [edge["node"]["title"] for edge in list_data["data"]["posts"]["edges"]]
        assert "Visible Post" in post_titles