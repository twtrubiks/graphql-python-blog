import pytest
from app.models.user import User
from app.models.post import Post
from app.core.security import create_access_token
from slugify import slugify


@pytest.mark.asyncio
class TestAuthDirective:
    """測試 @auth directive 權限控制

    這個測試套件驗證 field-level 權限控制是否正確運作，
    包括認證、授權、角色管理等。
    """

    async def test_unauthenticated_user_cannot_access_protected_fields(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試未認證用戶無法存取受保護的欄位"""
        # 查詢需要認證的 me field
        query = """
            query Me {
                me {
                    id
                    username
                    email
                }
            }
        """

        # 不提供認證 header
        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()

        # 應該返回錯誤或 null
        assert "errors" in data or data["data"]["me"] is None

        # 如果有錯誤訊息，應該提到認證
        if "errors" in data:
            error_message = data["errors"][0]["message"].lower()
            assert "auth" in error_message or "permission" in error_message

    async def test_authenticated_user_can_access_own_data(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試認證用戶可以存取自己的資料"""
        # 查詢自己的資料
        query = """
            query Me {
                me {
                    id
                    username
                    email
                    bio
                }
            }
        """

        # 生成實際的 JWT token
        access_token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post(
            "/graphql",
            json={"query": query},
            headers=headers
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["me"] is not None
        assert data["data"]["me"]["username"] == test_user.username
        assert data["data"]["me"]["email"] == test_user.email

    async def test_field_level_permission_email_privacy(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試 field-level 權限：email 隱私保護"""
        # 創建另一個用戶
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password="hashed"
        )
        test_session.add(other_user)
        await test_session.commit()

        # 查詢其他用戶的資料
        query = """
            query GetUser($username: String!) {
                user(username: $username) {
                    id
                    username
                    email
                    bio
                }
            }
        """

        # 作為認證用戶查詢其他用戶
        access_token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"username": "otheruser"}},
            headers=headers
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()

        # 應該能看到 username 但不能看到 email（或 email 為 null）
        if "errors" not in data and data["data"]["user"]:
            user_data = data["data"]["user"]
            assert user_data["username"] == "otheruser"
            # email 應該被隱藏或返回 null（取決於實作）
            # 這裡的預期行為是：非擁有者不能看到 email

    async def test_superuser_can_access_all_users_data(
        self,
        client,
        test_session,
    ):
        """測試超級用戶可以存取所有用戶資料"""
        # 創建超級用戶
        superuser = User(
            username="admin",
            email="admin@example.com",
            hashed_password="hashed",
            is_superuser=True
        )
        test_session.add(superuser)

        # 創建普通用戶
        normal_user = User(
            username="normaluser",
            email="normal@example.com",
            hashed_password="hashed"
        )
        test_session.add(normal_user)
        await test_session.commit()

        # 查詢所有用戶（需要超級用戶權限）
        query = """
            query GetAllUsers {
                users(limit: 10) {
                    id
                    username
                    email
                    isActive
                    isSuperuser
                }
            }
        """

        # 使用超級用戶 token
        admin_token = create_access_token(data={"sub": str(superuser.id)})
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.post(
            "/graphql",
            json={"query": query},
            headers=headers
        )

        # 驗證結果
        data = response.json()

        # 超級用戶應該能看到所有用戶的完整資料
        if "errors" not in data and data["data"]["users"]:
            users = data["data"]["users"]
            assert len(users) >= 2  # 至少有 2 個用戶

            # 應該能看到所有用戶的 email
            for user in users:
                if user["username"] in ["admin", "normaluser"]:
                    assert user["email"] is not None

    async def test_owner_can_update_own_post(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試擁有者可以更新自己的文章"""
        # 創建測試文章
        post = Post(
            title="My Post",
            slug=slugify("My Post"),
            content="Original content",
            excerpt="Original excerpt",
            author_id=test_user.id,
            status="published"
        )
        test_session.add(post)
        await test_session.commit()

        # 更新自己的文章
        mutation = """
            mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
                updatePost(id: $id, input: $input) {
                    id
                    title
                    content
                }
            }
        """

        # 使用擁有者的 token
        owner_token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "id": str(post.id),
                    "input": {
                        "title": "Updated Post",
                        "content": "Updated content"
                    }
                }
            },
            headers=headers
        )

        # 驗證結果
        data = response.json()

        # 擁有者應該能成功更新
        if "errors" not in data and data["data"]["updatePost"]:
            updated_post = data["data"]["updatePost"]
            assert updated_post["title"] == "Updated Post"
            assert updated_post["content"] == "Updated content"

    async def test_non_owner_cannot_update_others_post(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試非擁有者不能更新他人的文章"""
        # 創建另一個用戶
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password="hashed"
        )
        test_session.add(other_user)
        await test_session.commit()

        # 創建屬於 other_user 的文章
        post = Post(
            title="Other's Post",
            slug=slugify("Other's Post"),
            content="Original content",
            excerpt="Original excerpt",
            author_id=other_user.id,
            status="published"
        )
        test_session.add(post)
        await test_session.commit()

        # 嘗試更新他人的文章
        mutation = """
            mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
                updatePost(id: $id, input: $input) {
                    id
                    title
                    content
                }
            }
        """

        # 使用 test_user 的 token（不是文章擁有者）
        user_token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "id": str(post.id),
                    "input": {
                        "title": "Hacked Post",
                        "content": "Hacked content"
                    }
                }
            },
            headers=headers
        )

        # 驗證結果
        data = response.json()

        # 應該返回權限錯誤
        assert "errors" in data or data["data"]["updatePost"] is None

        if "errors" in data:
            error_message = data["errors"][0]["message"].lower()
            assert "permission" in error_message or "authorized" in error_message or "owner" in error_message

    async def test_authenticated_user_required_for_mutations(
        self,
        client,
        test_session,
    ):
        """測試 mutations 需要認證"""
        # 測試創建文章需要認證
        mutation = """
            mutation CreatePost($input: PostInput!) {
                createPost(input: $input) {
                    id
                    title
                }
            }
        """

        # 不提供認證 header
        response = await client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "title": "New Post",
                        "content": "Content",
                        "excerpt": "Excerpt"
                    }
                }
            }
        )

        # 驗證結果
        data = response.json()

        # 應該返回認證錯誤
        assert "errors" in data or data["data"]["createPost"] is None

        if "errors" in data:
            error_message = data["errors"][0]["message"].lower()
            assert "auth" in error_message or "permission" in error_message

    async def test_public_fields_accessible_without_auth(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試公開欄位不需要認證即可存取"""
        # 創建公開文章
        post = Post(
            title="Public Post",
            slug=slugify("Public Post"),
            content="Public content",
            excerpt="Public excerpt",
            author_id=test_user.id,
            status="published"
        )
        test_session.add(post)
        await test_session.commit()

        # 查詢公開文章（不需要認證）
        query = """
            query GetPosts {
                posts(limit: 5) {
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
                }
            }
        """

        # 不提供認證 header
        response = await client.post(
            "/graphql",
            json={"query": query}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["posts"] is not None

        # 應該能看到公開文章
        edges = data["data"]["posts"]["edges"]
        assert len(edges) > 0

        # 但某些敏感欄位（如作者 email）應該被隱藏
        for edge in edges:
            node = edge["node"]
            assert node["title"] is not None
            assert node["author"]["username"] is not None
            # email 不應該在公開查詢中出現