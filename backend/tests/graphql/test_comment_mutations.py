import pytest
from httpx import AsyncClient
from app.models.comment import Comment
from app.models.post import Post, PostStatus
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestAddCommentMutation:
    """測試新增評論 mutation"""
    
    async def test_add_comment_success(self, authenticated_client: AsyncClient, test_post):
        """測試成功新增評論"""
        mutation = """
        mutation AddComment($postId: ID!, $content: String!) {
            addComment(postId: $postId, content: $content) {
                id
                content
                author {
                    id
                    username
                }
                post {
                    id
                    title
                }
                createdAt
            }
        }
        """
        
        variables = {
            "postId": str(test_post.id),
            "content": "這是一個很棒的文章！"
        }
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["addComment"]
        
        assert data["id"] is not None
        assert data["content"] == "這是一個很棒的文章！"
        assert data["author"]["username"] == "testuser"
        assert data["post"]["id"] == test_post.id
        assert data["post"]["title"] == test_post.title
        assert data["createdAt"] is not None
    
    async def test_add_comment_without_auth(self, client: AsyncClient, test_post):
        """測試未登入無法新增評論"""
        mutation = """
        mutation AddComment($postId: ID!, $content: String!) {
            addComment(postId: $postId, content: $content) {
                id
                content
            }
        }
        """
        
        variables = {
            "postId": str(test_post.id),
            "content": "未登入評論"
        }
        
        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "登入" in errors[0]["message"] or "authentication" in errors[0]["message"].lower() or "unauthorized" in errors[0]["message"].lower()
    
    async def test_add_comment_to_nonexistent_post(self, authenticated_client: AsyncClient):
        """測試評論不存在的文章"""
        mutation = """
        mutation AddComment($postId: ID!, $content: String!) {
            addComment(postId: $postId, content: $content) {
                id
                content
            }
        }
        """
        
        variables = {
            "postId": "999999",
            "content": "評論不存在的文章"
        }
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower() or "找不到" in errors[0]["message"]
    
    async def test_add_comment_empty_content(self, authenticated_client: AsyncClient, test_post):
        """測試空內容評論"""
        mutation = """
        mutation AddComment($postId: ID!, $content: String!) {
            addComment(postId: $postId, content: $content) {
                id
                content
            }
        }
        """
        
        variables = {
            "postId": str(test_post.id),
            "content": ""
        }
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "empty" in errors[0]["message"].lower() or "內容不能為空" in errors[0]["message"].lower()
    
    async def test_add_comment_to_draft_post(self, authenticated_client: AsyncClient, test_session, test_user):
        """測試評論草稿文章"""
        # 創建草稿文章
        draft_post = Post(
            title="Draft Post",
            slug="draft-post",
            content="Draft content",
            status=PostStatus.DRAFT,
            author_id=test_user.id
        )
        test_session.add(draft_post)
        await test_session.commit()
        await test_session.refresh(draft_post)
        
        mutation = """
        mutation AddComment($postId: ID!, $content: String!) {
            addComment(postId: $postId, content: $content) {
                id
                content
            }
        }
        """
        
        variables = {
            "postId": str(draft_post.id),
            "content": "評論草稿"
        }
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        # 草稿文章可能允許作者評論，或完全禁止評論
        # 根據業務邏輯決定
        assert response.status_code == 200
        result = response.json()
        
        # 如果不允許評論草稿
        if "errors" in result:
            errors = result["errors"]
            assert "draft" in errors[0]["message"].lower() or "不能評論" in errors[0]["message"].lower()
        # 如果允許作者評論草稿
        else:
            data = result["data"]["addComment"]
            assert data["id"] is not None


@pytest.mark.asyncio
class TestDeleteCommentMutation:
    """測試刪除評論 mutation"""
    
    async def test_delete_own_comment(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """測試刪除自己的評論"""
        # 創建評論
        comment = Comment(
            content="我的評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)
        
        mutation = """
        mutation DeleteComment($commentId: ID!) {
            deleteComment(commentId: $commentId) {
                success
                message
            }
        }
        """
        
        variables = {"commentId": str(comment.id)}
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["deleteComment"]
        assert data["success"] is True
        
        # 驗證評論已被刪除（軟刪除）
        await test_session.refresh(comment)
        assert comment.deleted_at is not None
    
    async def test_post_author_delete_comment(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """測試文章作者可以刪除文章下的評論"""
        # 創建其他用戶
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash("password")
        )
        test_session.add(other_user)
        await test_session.commit()
        
        # 創建其他用戶的評論
        comment = Comment(
            content="其他用戶的評論",
            user_id=other_user.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)
        
        mutation = """
        mutation DeleteComment($commentId: ID!) {
            deleteComment(commentId: $commentId) {
                success
                message
            }
        }
        """
        
        variables = {"commentId": str(comment.id)}
        
        # 文章作者身份刪除評論
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["deleteComment"]
        assert data["success"] is True
        
        # 驗證評論已被刪除
        await test_session.refresh(comment)
        assert comment.deleted_at is not None
    
    async def test_cannot_delete_others_comment(self, authenticated_client: AsyncClient, test_session, test_user):
        """測試不能刪除別人的評論（非文章作者）"""
        # 創建其他用戶和文章
        other_user = User(
            email="author@example.com",
            username="authoruser",
            hashed_password=get_password_hash("password")
        )
        test_session.add(other_user)
        await test_session.commit()
        
        other_post = Post(
            title="Other Post",
            slug="other-post",
            content="Other content",
            status=PostStatus.PUBLISHED,
            author_id=other_user.id
        )
        test_session.add(other_post)
        await test_session.commit()
        
        # 創建其他用戶的評論
        comment = Comment(
            content="其他用戶的評論",
            user_id=other_user.id,
            post_id=other_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)
        
        mutation = """
        mutation DeleteComment($commentId: ID!) {
            deleteComment(commentId: $commentId) {
                success
                message
            }
        }
        """
        
        variables = {"commentId": str(comment.id)}
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        errors = response.json().get("errors")
        if errors:
            assert "permission" in errors[0]["message"].lower() or "權限" in errors[0]["message"].lower()
        else:
            data = response.json()["data"]["deleteComment"]
            assert data["success"] is False
            assert "permission" in data["message"].lower() or "權限" in data["message"].lower()
    
    async def test_delete_nonexistent_comment(self, authenticated_client: AsyncClient):
        """測試刪除不存在的評論"""
        mutation = """
        mutation DeleteComment($commentId: ID!) {
            deleteComment(commentId: $commentId) {
                success
                message
            }
        }
        """
        
        variables = {"commentId": "999999"}
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        
        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower() or "找不到" in errors[0]["message"]