import pytest
from datetime import datetime
from app.models.post import PostStatus


class TestCreatePostMutation:
    """測試 createPost mutation"""
    
    @pytest.mark.asyncio
    async def test_create_post_success(self, authenticated_client, test_session):
        """測試：成功建立文章（需要認證）"""
        
        # GraphQL mutation 查詢
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
        
        # 準備測試資料
        variables = {
            "input": {
                "title": "My First Blog Post",
                "content": "This is the content of my first blog post. It's quite interesting!",
                "excerpt": "A brief excerpt of my post",
                "status": "DRAFT"
            }
        }
        
        # 發送請求（使用已認證的客戶端）
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        # 驗證回應
        assert response.status_code == 200
        data = response.json()
        
        # 確認沒有錯誤
        assert "errors" not in data
        # 驗證返回的資料
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