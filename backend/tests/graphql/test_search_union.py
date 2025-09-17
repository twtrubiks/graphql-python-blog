import pytest
from datetime import datetime
from typing import List, Dict, Any
from slugify import slugify

from app.models.user import User
from app.models.post import Post


@pytest.mark.asyncio
class TestSearchUnionTypes:
    """測試 Union Types 搜尋功能"""

    async def test_search_returns_post_results(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試搜尋返回文章結果"""
        # 創建測試文章
        post1 = Post(
            title="Python GraphQL Tutorial",
            slug=slugify("Python GraphQL Tutorial"),
            content="Learn how to build APIs with GraphQL",
            excerpt="A comprehensive guide to GraphQL",
            author_id=test_user.id,
            status="published",
        )
        post2 = Post(
            title="Advanced Python Techniques",
            slug=slugify("Advanced Python Techniques"),
            content="Deep dive into Python internals",
            excerpt="Master Python programming",
            author_id=test_user.id,
            status="published",
        )
        post3 = Post(
            title="JavaScript Basics",
            slug=slugify("JavaScript Basics"),
            content="Introduction to JavaScript",
            excerpt="Learn JavaScript from scratch",
            author_id=test_user.id,
            status="published",
        )

        test_session.add_all([post1, post2, post3])
        await test_session.commit()

        # 執行搜尋查詢
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                        excerpt
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                        bio
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "Python"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        assert len(results) == 2  # 應該找到 2 篇包含 "Python" 的文章

        # 驗證返回的都是 Post 類型
        for result in results:
            assert result["__typename"] == "PostType"
            assert "Python" in result["title"]
            assert "postId" in result or "userId" in result
            assert "excerpt" in result

    async def test_search_returns_user_results(
        self,
        client,
        test_session,
    ):
        """測試搜尋返回用戶結果"""
        # 創建測試用戶
        user1 = User(
            username="pythonista",
            email="python@example.com",
            bio="Python developer and enthusiast",
            hashed_password="hashed"
        )
        user2 = User(
            username="jsdev",
            email="js@example.com",
            bio="JavaScript and Python developer",
            hashed_password="hashed"
        )
        user3 = User(
            username="rustacean",
            email="rust@example.com",
            bio="Rust programming expert",
            hashed_password="hashed"
        )

        test_session.add_all([user1, user2, user3])
        await test_session.commit()

        # 執行搜尋查詢
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                        excerpt
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                        bio
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "python"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        assert len(results) >= 2  # 應該找到至少 2 個包含 "python" 的用戶

        # 驗證返回的用戶
        user_results = [r for r in results if r["__typename"] == "UserType"]
        assert len(user_results) >= 2

        for result in user_results:
            assert result["__typename"] == "UserType"
            assert ("python" in result["username"].lower() or
                   "python" in result.get("bio", "").lower())

    async def test_search_returns_mixed_results(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試混合結果型別處理"""
        # 創建測試數據
        post = Post(
            title="GraphQL Best Practices",
            slug=slugify("GraphQL Best Practices"),
            content="Learn GraphQL best practices",
            excerpt="Essential GraphQL patterns",
            author_id=test_user.id,
            status="published",
        )

        user = User(
            username="graphql_expert",
            email="graphql@example.com",
            bio="GraphQL consultant and trainer",
            hashed_password="hashed"
        )

        test_session.add_all([post, user])
        await test_session.commit()

        # 執行搜尋查詢
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                        excerpt
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                        bio
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "GraphQL"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        assert len(results) >= 2  # 應該包含文章和用戶

        # 檢查是否有不同類型的結果
        types = {result["__typename"] for result in results}
        assert "PostType" in types
        assert "UserType" in types

        # 驗證每個結果都包含搜尋詞
        for result in results:
            if result["__typename"] == "PostType":
                assert "GraphQL" in result["title"]
            elif result["__typename"] == "UserType":
                assert ("graphql" in result["username"].lower() or
                       "GraphQL" in result.get("bio", ""))

    async def test_search_empty_results(
        self,
        client,
        test_session,
    ):
        """測試空搜尋結果"""
        # 先創建一個用戶作為文章作者
        author = User(
            username="test_author",
            email="author@example.com",
            bio="Test author",
            hashed_password="hashed"
        )
        test_session.add(author)
        await test_session.flush()  # 先 flush 以獲取 author.id

        # 創建一些不匹配的數據
        post = Post(
            title="Java Programming",
            slug=slugify("Java Programming"),
            content="Learn Java",
            excerpt="Java basics",
            status="published",
            author_id=author.id  # 使用實際創建的用戶 ID
        )

        # 創建另一個用戶
        user = User(
            username="java_dev",
            email="java@example.com",
            bio="Java developer",
            hashed_password="hashed"
        )

        test_session.add_all([post, user])
        await test_session.commit()

        # 執行搜尋查詢
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                        excerpt
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                        bio
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "NonExistentTerm"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        assert results == []  # 應該返回空列表

    async def test_search_case_insensitive(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試搜尋不區分大小寫"""
        # 創建測試數據
        post = Post(
            title="PYTHON Programming Guide",
            slug=slugify("PYTHON Programming Guide"),
            content="Learn Python",
            excerpt="Python tutorial",
            author_id=test_user.id,
            status="published",
        )

        user = User(
            username="PYTHON_MASTER",
            email="python2@example.com",
            bio="Python expert",
            hashed_password="hashed"
        )

        test_session.add_all([post, user])
        await test_session.commit()

        # 執行搜尋查詢（使用小寫）
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "python"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        assert len(results) >= 2  # 應該找到文章和用戶

        # 檢查是否包含不同大小寫的結果
        post_results = [r for r in results if r["__typename"] == "PostType"]
        user_results = [r for r in results if r["__typename"] == "UserType"]

        assert len(post_results) >= 1
        assert len(user_results) >= 1

    async def test_search_only_published_posts(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試搜尋只返回已發布的文章"""
        # 創建不同狀態的文章
        published_post = Post(
            title="Python Tutorial",
            slug=slugify("Python Tutorial"),
            content="Learn Python",
            excerpt="Python guide",
            author_id=test_user.id,
            status="published",
        )

        draft_post = Post(
            title="Python Advanced",
            slug=slugify("Python Advanced"),
            content="Advanced Python",
            excerpt="Advanced guide",
            author_id=test_user.id,
            status="draft",
        )

        test_session.add_all([published_post, draft_post])
        await test_session.commit()

        # 執行搜尋查詢
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "Python"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        post_results = [r for r in results if r["__typename"] == "PostType"]

        # 應該只找到 1 篇已發布的文章
        assert len(post_results) == 1
        assert post_results[0]["title"] == "Python Tutorial"

    async def test_search_with_special_characters(
        self,
        client,
        test_session,
        test_user,
    ):
        """測試包含特殊字符的搜尋"""
        # 創建包含特殊字符的數據
        post = Post(
            title="C++ Programming Guide",
            slug=slugify("C++ Programming Guide"),
            content="Learn C++",
            excerpt="C++ tutorial",
            author_id=test_user.id,
            status="published",
        )

        user = User(
            username="cpp_dev",
            email="cpp@example.com",
            bio="C++ developer",
            hashed_password="hashed"
        )

        test_session.add_all([post, user])
        await test_session.commit()

        # 執行搜尋查詢
        query = """
            query SimpleSearch($term: String!) {
                search(term: $term) {
                    ... on PostType {
                        __typename
                        postId: id
                        title
                    }
                    ... on UserType {
                        __typename
                        userId: id
                        username
                        bio
                    }
                }
            }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"term": "C++"}}
        )

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert "data" in data

        results = data["data"]["search"]
        assert len(results) >= 1  # 應該至少找到文章

        post_results = [r for r in results if r["__typename"] == "PostType"]
        assert len(post_results) >= 1
        assert "C++" in post_results[0]["title"]