import pytest
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from app.models.comment import Comment
from app.models.post import Post, PostStatus
from app.models.user import User
from app.core.security import get_password_hash
from app.graphql.subscriptions.comment import CommentUpdatedEvent, CommentDeletedEvent


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
    
    async def test_add_comment_to_soft_deleted_post_fails(self, authenticated_client: AsyncClient, test_session, test_post):
        """測試對已軟刪除的文章留言會失敗（即使 status 仍是 PUBLISHED）"""
        post = await test_session.get(Post, test_post.id)
        post.deleted_at = datetime.now(timezone.utc)
        await test_session.commit()

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
            "content": "對已刪除文章的評論"
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower()

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
    
    async def test_delete_comment_publishes_deleted_event(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """刪除評論後應推送 commentDeleted 事件（含剩餘留言數）給該文章的訂閱者"""
        kept = Comment(content="保留的評論", user_id=test_user.id, post_id=test_post.id)
        target = Comment(content="要刪的評論", user_id=test_user.id, post_id=test_post.id)
        test_session.add_all([kept, target])
        await test_session.commit()
        await test_session.refresh(target)

        queue = CommentDeletedEvent.subscribe(str(test_post.id))
        try:
            mutation = """
            mutation DeleteComment($commentId: ID!) {
                deleteComment(commentId: $commentId) { success }
            }
            """
            response = await authenticated_client.post(
                "/graphql",
                json={"query": mutation, "variables": {"commentId": str(target.id)}}
            )
            assert response.status_code == 200
            assert response.json()["data"]["deleteComment"]["success"] is True

            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert event.comment_id == str(target.id)
            assert event.post_id == str(test_post.id)
            # 刪除後剩 1 則未刪除的評論
            assert event.total_comments == 1
        finally:
            CommentDeletedEvent.unsubscribe(str(test_post.id), queue)

    async def test_failed_delete_does_not_publish_event(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """刪除失敗（無權限）時不應推送任何事件"""
        other_user = User(
            email="stranger@example.com",
            username="stranger",
            hashed_password=get_password_hash("password")
        )
        test_session.add(other_user)
        await test_session.commit()

        other_post = Post(
            title="別人的文章", content="...", slug="others-post",
            author_id=other_user.id, status=PostStatus.PUBLISHED
        )
        test_session.add(other_post)
        await test_session.commit()

        comment = Comment(content="別人的評論", user_id=other_user.id, post_id=other_post.id)
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        queue = CommentDeletedEvent.subscribe(str(other_post.id))
        try:
            mutation = """
            mutation DeleteComment($commentId: ID!) {
                deleteComment(commentId: $commentId) { success }
            }
            """
            response = await authenticated_client.post(
                "/graphql",
                json={"query": mutation, "variables": {"commentId": str(comment.id)}}
            )
            assert "errors" in response.json()
            assert queue.empty()
        finally:
            CommentDeletedEvent.unsubscribe(str(other_post.id), queue)

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


@pytest.mark.asyncio
class TestUpdateCommentMutation:
    """測試編輯評論 mutation"""

    async def test_update_own_comment_success(
        self, authenticated_client: AsyncClient, test_session, test_user, test_post
    ):
        """測試成功編輯自己的評論"""
        # 創建評論
        comment = Comment(
            content="原始內容",
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        mutation = """
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
                comment {
                    id
                    content
                    updatedAt
                }
            }
        }
        """

        variables = {
            "commentId": str(comment.id),
            "input": {"content": "已編輯的內容"}
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        result = response.json()
        assert "errors" not in result

        data = result["data"]["updateComment"]
        assert data["success"] is True
        assert data["comment"]["content"] == "已編輯的內容"
        # updated_at 應該被更新
        assert data["comment"]["updatedAt"] is not None

    async def test_update_comment_empty_content(
        self, authenticated_client: AsyncClient, test_session, test_user, test_post
    ):
        """測試空內容應該失敗"""
        comment = Comment(
            content="原始內容",
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        mutation = """
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
            }
        }
        """

        variables = {
            "commentId": str(comment.id),
            "input": {"content": ""}
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "空" in errors[0]["message"] or "empty" in errors[0]["message"].lower()

    async def test_cannot_update_others_comment(
        self, authenticated_client: AsyncClient, test_session, test_user, test_post
    ):
        """測試不能編輯別人的評論"""
        # 創建其他用戶
        other_user = User(
            email="other_update@example.com",
            username="other_update_user",
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
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
            }
        }
        """

        variables = {
            "commentId": str(comment.id),
            "input": {"content": "嘗試編輯"}
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "權限" in errors[0]["message"] or "permission" in errors[0]["message"].lower()

    async def test_post_author_cannot_update_others_comment(
        self, authenticated_client: AsyncClient, test_session, test_user, test_post
    ):
        """測試文章作者不能編輯別人的評論（與刪除不同）"""
        # 創建其他用戶
        commenter = User(
            email="commenter_update@example.com",
            username="commenter_update",
            hashed_password=get_password_hash("password")
        )
        test_session.add(commenter)
        await test_session.commit()

        # 其他用戶在 test_user 的文章下評論
        # test_post 的作者是 test_user
        comment = Comment(
            content="評論者的評論",
            user_id=commenter.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        mutation = """
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
            }
        }
        """

        variables = {
            "commentId": str(comment.id),
            "input": {"content": "文章作者嘗試編輯"}
        }

        # 以文章作者（test_user）身份嘗試編輯
        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        # 即使是文章作者，也不能編輯別人的評論
        assert errors is not None
        assert "權限" in errors[0]["message"] or "permission" in errors[0]["message"].lower()

    async def test_update_comment_publishes_updated_event(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """編輯評論後應推送 commentUpdated 事件（含新內容與作者）給該文章的訂閱者"""
        comment = Comment(content="原始內容", user_id=test_user.id, post_id=test_post.id)
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        queue = CommentUpdatedEvent.subscribe(str(test_post.id))
        try:
            mutation = """
            mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
                updateComment(commentId: $commentId, input: $input) { success }
            }
            """
            response = await authenticated_client.post(
                "/graphql",
                json={
                    "query": mutation,
                    "variables": {"commentId": str(comment.id), "input": {"content": "修改後內容"}}
                }
            )
            assert response.status_code == 200
            assert response.json()["data"]["updateComment"]["success"] is True

            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert event.id == str(comment.id)
            assert event.content == "修改後內容"
            assert event.author is not None
            assert event.author.username == test_user.username
        finally:
            CommentUpdatedEvent.unsubscribe(str(test_post.id), queue)

    async def test_failed_update_does_not_publish_event(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """編輯失敗（內容為空）時不應推送任何事件"""
        comment = Comment(content="原始內容", user_id=test_user.id, post_id=test_post.id)
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        queue = CommentUpdatedEvent.subscribe(str(test_post.id))
        try:
            mutation = """
            mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
                updateComment(commentId: $commentId, input: $input) { success }
            }
            """
            response = await authenticated_client.post(
                "/graphql",
                json={
                    "query": mutation,
                    "variables": {"commentId": str(comment.id), "input": {"content": "   "}}
                }
            )
            assert "errors" in response.json()
            assert queue.empty()
        finally:
            CommentUpdatedEvent.unsubscribe(str(test_post.id), queue)

    async def test_update_nonexistent_comment(self, authenticated_client: AsyncClient):
        """測試編輯不存在的評論"""
        mutation = """
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
            }
        }
        """

        variables = {
            "commentId": "999999",
            "input": {"content": "編輯不存在的評論"}
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "不存在" in errors[0]["message"] or "not found" in errors[0]["message"].lower() or "找不到" in errors[0]["message"]

    async def test_update_deleted_comment(
        self, authenticated_client: AsyncClient, test_session, test_user, test_post
    ):
        """測試不能編輯已刪除的評論"""
        comment = Comment(
            content="已刪除的評論",
            user_id=test_user.id,
            post_id=test_post.id,
            deleted_at=datetime.now(timezone.utc)  # 標記為已刪除
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        mutation = """
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
            }
        }
        """

        variables = {
            "commentId": str(comment.id),
            "input": {"content": "嘗試編輯已刪除評論"}
        }

        response = await authenticated_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "刪除" in errors[0]["message"] or "deleted" in errors[0]["message"].lower()

    async def test_update_comment_without_auth(
        self, client: AsyncClient, test_session, test_user, test_post
    ):
        """測試未登入無法編輯評論"""
        comment = Comment(
            content="評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        mutation = """
        mutation UpdateComment($commentId: ID!, $input: UpdateCommentInput!) {
            updateComment(commentId: $commentId, input: $input) {
                success
                message
            }
        }
        """

        variables = {
            "commentId": str(comment.id),
            "input": {"content": "未登入編輯"}
        }

        response = await client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        errors = response.json().get("errors")
        assert errors is not None
        assert "登入" in errors[0]["message"] or "authentication" in errors[0]["message"].lower() or "unauthorized" in errors[0]["message"].lower()