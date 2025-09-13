"""評論系統整合測試"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.models.user import User
from app.core.security import get_password_hash, create_access_token
from app.main import app


@pytest.mark.asyncio
async def test_complete_comment_flow(authenticated_client: AsyncClient, test_post):
    """測試完整的評論流程：創建、查詢、刪除"""
    
    # 1. 創建評論
    create_mutation = """
    mutation AddComment($postId: ID!, $content: String!) {
        addComment(postId: $postId, content: $content) {
            id
            content
            author {
                username
            }
            createdAt
        }
    }
    """
    
    create_response = await authenticated_client.post(
        "/graphql",
        json={
            "query": create_mutation,
            "variables": {
                "postId": str(test_post.id),
                "content": "這是一個整合測試評論"
            }
        }
    )
    
    assert create_response.status_code == 200
    comment_data = create_response.json()["data"]["addComment"]
    comment_id = comment_data["id"]
    assert comment_data["content"] == "這是一個整合測試評論"
    assert comment_data["author"]["username"] == "testuser"
    
    # 2. 查詢文章評論
    query = """
    query GetPost($id: ID!) {
        post(id: $id) {
            id
            title
            comments {
                id
                content
                author {
                    username
                }
            }
            totalComments
        }
    }
    """
    
    query_response = await authenticated_client.post(
        "/graphql",
        json={
            "query": query,
            "variables": {"id": str(test_post.id)}
        }
    )
    
    assert query_response.status_code == 200
    post_data = query_response.json()["data"]["post"]
    assert post_data["totalComments"] == 1
    assert len(post_data["comments"]) == 1
    assert post_data["comments"][0]["content"] == "這是一個整合測試評論"
    
    # 3. 刪除評論
    delete_mutation = """
    mutation DeleteComment($commentId: ID!) {
        deleteComment(commentId: $commentId) {
            success
            message
        }
    }
    """
    
    delete_response = await authenticated_client.post(
        "/graphql",
        json={
            "query": delete_mutation,
            "variables": {"commentId": comment_id}
        }
    )
    
    assert delete_response.status_code == 200
    delete_data = delete_response.json()["data"]["deleteComment"]
    assert delete_data["success"] is True
    
    # 4. 驗證評論已被刪除
    final_query_response = await authenticated_client.post(
        "/graphql",
        json={
            "query": query,
            "variables": {"id": str(test_post.id)}
        }
    )
    
    assert final_query_response.status_code == 200
    final_post_data = final_query_response.json()["data"]["post"]
    assert final_post_data["totalComments"] == 0
    assert len(final_post_data["comments"]) == 0


@pytest.mark.asyncio
async def test_multiple_users_commenting(test_session, authenticated_client, test_post):
    """測試多個用戶評論同一篇文章"""
    # 創建第二個用戶
    user2 = User(
        email="user2@example.com",
        username="user2",
        hashed_password=get_password_hash("password")
    )
    test_session.add(user2)
    await test_session.commit()
    await test_session.refresh(user2)
    
    # 創建第二個用戶的客戶端
    token2 = create_access_token(data={"sub": str(user2.id)})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client2:
        client2.headers.update({"Authorization": f"Bearer {token2}"})
        
        # 用戶1評論
        mutation = """
        mutation AddComment($postId: ID!, $content: String!) {
            addComment(postId: $postId, content: $content) {
                id
                content
                author {
                    username
                }
            }
        }
        """
        
        response1 = await authenticated_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "postId": str(test_post.id),
                    "content": "用戶1的評論"
                }
            }
        )
        
        assert response1.status_code == 200
        comment1 = response1.json()["data"]["addComment"]
        assert comment1["author"]["username"] == "testuser"
        
        # 用戶2評論
        response2 = await client2.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "postId": str(test_post.id),
                    "content": "用戶2的評論"
                }
            }
        )
        
        assert response2.status_code == 200
        comment2 = response2.json()["data"]["addComment"]
        assert comment2["author"]["username"] == "user2"
        
        # 查詢所有評論
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                comments {
                    content
                    author {
                        username
                    }
                }
                totalComments
            }
        }
        """
        
        query_response = await authenticated_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"id": str(test_post.id)}
            }
        )
        
        assert query_response.status_code == 200
        post_data = query_response.json()["data"]["post"]
        assert post_data["totalComments"] == 2
        
        # 驗證兩個評論都存在
        comments = post_data["comments"]
        assert len(comments) == 2
        usernames = [c["author"]["username"] for c in comments]
        assert "testuser" in usernames
        assert "user2" in usernames