import pytest
from app.models.post import Post
from app.models.comment import Comment
from slugify import slugify


@pytest.mark.asyncio
class TestFragmentReuse:
    """測試 Fragment 重用提升程式碼維護性

    Fragment 是 GraphQL 客戶端的功能，用於重用查詢片段。
    這裡測試 Fragment 在實際查詢中的應用。
    """

    async def test_fragment_in_multiple_queries(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試 Fragment 在多個查詢中重用"""
        # 創建測試文章
        post1 = Post(
            title="GraphQL Best Practices",
            slug=slugify("GraphQL Best Practices"),
            content="Learn GraphQL best practices",
            excerpt="Essential GraphQL patterns",
            author_id=test_user.id,
            status="published",
        )
        post2 = Post(
            title="Python Tips",
            slug=slugify("Python Tips"),
            content="Python programming tips",
            excerpt="Useful Python tips",
            author_id=test_user.id,
            status="published",
        )

        test_session.add_all([post1, post2])
        await test_session.commit()

        # 使用 Fragment 的查詢
        # Fragment 定義在查詢字串中
        query = """
            fragment AuthorInfo on UserType {
                id
                username
                email
                bio
            }

            fragment PostBasicInfo on PostType {
                id
                title
                slug
                excerpt
                createdAt
            }

            query GetPostsWithAuthor {
                posts(limit: 10) {
                    edges {
                        node {
                            ...PostBasicInfo
                            author {
                                ...AuthorInfo
                            }
                        }
                    }
                }

                me {
                    ...AuthorInfo
                }
            }
        """

        # 需要認證
        headers = {"Authorization": f"Bearer test-token"}
        response = await client.post(
            "/graphql",
            json={"query": query},
            headers=headers
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        # 驗證 posts 查詢使用了 Fragment
        posts_data = data["data"]["posts"]
        assert posts_data is not None
        assert "edges" in posts_data

        # 每個 post 應該包含 Fragment 定義的欄位
        for edge in posts_data["edges"]:
            node = edge["node"]
            assert "id" in node
            assert "title" in node
            assert "slug" in node
            assert "excerpt" in node
            assert "createdAt" in node

            # author 應該包含 AuthorInfo Fragment 的欄位
            if "author" in node:
                author = node["author"]
                assert "id" in author
                assert "username" in author

        # 驗證 me 查詢也使用了同樣的 Fragment
        me_data = data["data"]["me"]
        if me_data:
            assert "id" in me_data
            assert "username" in me_data
            assert "email" in me_data
            # bio 可能是 None，但欄位應該存在
            assert "bio" in me_data

    async def test_nested_fragments(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試 Fragment 巢狀使用"""
        # 創建測試數據
        post = Post(
            title="Test Post",
            slug=slugify("Test Post"),
            content="Test content",
            excerpt="Test excerpt",
            author_id=test_user.id,
            status="published",
        )

        comment = Comment(
            content="Great post!",
            post_id=1,  # 將在 commit 後更新
            user_id=test_user.id,
        )

        test_session.add(post)
        await test_session.commit()

        comment.post_id = post.id
        test_session.add(comment)
        await test_session.commit()

        # 使用巢狀 Fragment 的查詢
        query = """
            fragment UserBasic on UserType {
                id
                username
            }

            fragment CommentWithAuthor on Comment {
                id
                content
                createdAt
                author {
                    ...UserBasic
                }
            }

            fragment PostFull on PostType {
                id
                title
                content
                excerpt
                author {
                    ...UserBasic
                    bio
                }
                comments {
                    ...CommentWithAuthor
                }
            }

            query GetPostWithDetails($id: ID!) {
                post(id: $id) {
                    ...PostFull
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"id": str(post.id)}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        post_data = data["data"]["post"]
        assert post_data is not None

        # 驗證 PostFull Fragment 的欄位
        assert post_data["id"] == post.id
        assert post_data["title"] == "Test Post"
        assert "content" in post_data
        assert "excerpt" in post_data

        # 驗證巢狀的 UserBasic Fragment
        assert "author" in post_data
        author = post_data["author"]
        assert "id" in author
        assert "username" in author
        assert "bio" in author  # 這個是額外添加的

        # 驗證 CommentWithAuthor Fragment
        assert "comments" in post_data
        comments = post_data["comments"]
        assert len(comments) == 1
        comment_data = comments[0]
        assert comment_data["content"] == "Great post!"
        assert "author" in comment_data
        assert comment_data["author"]["username"] == test_user.username

    async def test_fragment_type_safety(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試 Fragment 型別安全性"""
        # 創建測試文章
        post = Post(
            title="Type Safety Test",
            slug=slugify("Type Safety Test"),
            content="Testing type safety",
            excerpt="Type safety",
            author_id=test_user.id,
            status="published",
        )

        test_session.add(post)
        await test_session.commit()

        # 測試正確的 Fragment 使用
        valid_query = """
            fragment PostFields on PostType {
                id
                title
                slug
            }

            query GetPost($id: ID!) {
                post(id: $id) {
                    ...PostFields
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": valid_query, "variables": {"id": str(post.id)}}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["post"]["title"] == "Type Safety Test"

        # 測試錯誤的 Fragment 使用（Fragment 定義在錯誤的類型上）
        # 注意：這個測試應該失敗，因為 PostFields 不能用在 UserType 上
        invalid_query = """
            fragment PostFields on PostType {
                id
                title
                slug
            }

            query GetUser {
                me {
                    ...PostFields
                }
            }
        """

        headers = {"Authorization": f"Bearer test-token"}
        response = await client.post(
            "/graphql",
            json={"query": invalid_query},
            headers=headers
        )

        # 這個查詢應該返回錯誤
        data = response.json()
        assert "errors" in data or (data["data"]["me"] and "title" not in data["data"]["me"])

    async def test_fragment_reduces_duplication(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試 Fragment 減少重複程式碼"""
        # 創建多個測試文章
        posts = []
        for i in range(3):
            post = Post(
                title=f"Post {i+1}",
                slug=slugify(f"Post {i+1}"),
                content=f"Content {i+1}",
                excerpt=f"Excerpt {i+1}",
                author_id=test_user.id,
                status="published",
            )
            posts.append(post)

        test_session.add_all(posts)
        await test_session.commit()

        # 不使用 Fragment 的查詢（重複的欄位定義）
        query_without_fragment = """
            query GetPostsWithoutFragment {
                posts(limit: 3) {
                    edges {
                        node {
                            id
                            title
                            slug
                            excerpt
                            createdAt
                            updatedAt
                            author {
                                id
                                username
                                email
                            }
                        }
                    }
                }
            }
        """

        # 使用 Fragment 的查詢（避免重複）
        query_with_fragment = """
            fragment PostDetails on PostType {
                id
                title
                slug
                excerpt
                createdAt
                updatedAt
                author {
                    id
                    username
                    email
                }
            }

            query GetPostsWithFragment {
                posts(limit: 3) {
                    edges {
                        node {
                            ...PostDetails
                        }
                    }
                }
            }
        """

        # 兩個查詢應該返回相同的結果結構
        response1 = await client.post(
            "/graphql",
            json={"query": query_without_fragment}
        )

        response2 = await client.post(
            "/graphql",
            json={"query": query_with_fragment}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert "errors" not in data1
        assert "errors" not in data2

        # 驗證兩個查詢返回相同的欄位結構
        posts1 = data1["data"]["posts"]["edges"]
        posts2 = data2["data"]["posts"]["edges"]

        assert len(posts1) == len(posts2)

        for i in range(len(posts1)):
            node1 = posts1[i]["node"]
            node2 = posts2[i]["node"]

            # 驗證包含相同的欄位
            assert set(node1.keys()) == set(node2.keys())
            assert node1["title"] == node2["title"]

            if "author" in node1:
                assert set(node1["author"].keys()) == set(node2["author"].keys())

    async def test_fragment_with_variables(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試 Fragment 與變數配合使用"""
        # 創建測試文章和評論
        post = Post(
            title="Fragment Variables Test",
            slug=slugify("Fragment Variables Test"),
            content="Testing fragments with variables",
            excerpt="Test excerpt",
            author_id=test_user.id,
            status="published",
        )

        test_session.add(post)
        await test_session.commit()

        # 添加多個評論
        for i in range(5):
            comment = Comment(
                content=f"Comment {i+1}",
                post_id=post.id,
                user_id=test_user.id,
            )
            test_session.add(comment)

        await test_session.commit()

        # 使用 Fragment 和變數的查詢
        query = """
            fragment PostWithComments on PostType {
                id
                title
                comments(limit: $commentLimit, offset: $commentOffset) {
                    id
                    content
                }
            }

            query GetPostWithLimitedComments(
                $postId: ID!,
                $commentLimit: Int,
                $commentOffset: Int
            ) {
                post(id: $postId) {
                    ...PostWithComments
                }
            }
        """

        # 測試不同的變數值
        # 獲取前 2 個評論
        response1 = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "postId": str(post.id),
                    "commentLimit": 2,
                    "commentOffset": 0
                }
            }
        )

        # 獲取接下來的 2 個評論
        response2 = await client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "postId": str(post.id),
                    "commentLimit": 2,
                    "commentOffset": 2
                }
            }
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert "errors" not in data1
        assert "errors" not in data2

        # 驗證返回不同的評論
        comments1 = data1["data"]["post"]["comments"]
        comments2 = data2["data"]["post"]["comments"]

        assert len(comments1) == 2
        assert len(comments2) == 2

        # 確保是不同的評論
        comment_ids1 = {c["id"] for c in comments1}
        comment_ids2 = {c["id"] for c in comments2}
        assert comment_ids1.isdisjoint(comment_ids2)  # 沒有交集