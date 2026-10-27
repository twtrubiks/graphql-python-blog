import pytest
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from app.models.comment import Comment
from app.models.post import Post, PostStatus
from app.models.user import User
from app.core.security import get_password_hash
from app.graphql.subscriptions.comment import CommentUpdatedEvent, CommentDeletedEvent

DELETE_COMMENT_MUTATION = """
mutation DeleteComment($commentId: ID!) {
    deleteComment(commentId: $commentId) {
        success
        message
    }
}
"""


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
                isDeleted
                deletedAt
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
        # 前端用 isDeleted 決定要不要顯示這則留言
        assert data["isDeleted"] is False
        assert data["deletedAt"] is None
    
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
        # 精確比對：錯誤訊息可能夾帶 SQL 參數（含送出的內容「未登入…」），用關鍵字比對會碰巧通過
        assert errors[0]["message"] == "需要登入才能評論"
    
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
        assert errors[0]["message"] == "文章不存在"

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
        assert errors[0]["message"] == "文章不存在"
    
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
        assert errors[0]["message"] == "評論內容不能為空"
    
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
        
        # 作者可以評論自己的草稿（他人不行，見 test_cannot_comment_on_others_draft）
        assert response.status_code == 200
        result = response.json()
        assert "errors" not in result
        assert result["data"]["addComment"]["content"] == "評論草稿"

    async def test_cannot_comment_on_others_draft(self, authenticated_client: AsyncClient, test_session, user_factory):
        """不能評論別人尚未發布的文章"""
        author = await user_factory.create()
        draft_post = Post(
            title="Others Draft",
            slug="others-draft",
            content="Draft content",
            status=PostStatus.DRAFT,
            author_id=author.id
        )
        test_session.add(draft_post)
        await test_session.commit()

        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": 'mutation AddComment($postId: ID!) { addComment(postId: $postId, content: "hi") { id } }',
                "variables": {"postId": str(draft_post.id)}
            }
        )

        data = response.json()
        assert data["data"] is None
        assert data["errors"][0]["message"] == "不能評論未發布的文章"


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
        assert data["message"] == "評論已成功刪除"
        
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
        assert data["message"] == "評論已成功刪除"
        
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
        data = response.json()
        assert data["data"] is None
        assert data["errors"][0]["message"] == "沒有權限刪除此評論"
    
    async def test_delete_comment_publishes_deleted_event(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """刪除評論後應推送 commentDeleted 事件（含剩餘留言數）給該文章的訂閱者"""
        # 保留 2 則、刪除 1 則：數量不同，計數條件寫反（只算已刪除的）才會被抓到
        kept = [Comment(content=f"保留的評論 {i}", user_id=test_user.id, post_id=test_post.id) for i in range(2)]
        target = Comment(content="要刪的評論", user_id=test_user.id, post_id=test_post.id)
        test_session.add_all([*kept, target])
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
            # 刪除後剩 2 則未刪除的評論
            assert event.total_comments == 2
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
            assert response.json()["errors"][0]["message"] == "沒有權限刪除此評論"
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
        assert errors[0]["message"] == "評論不存在"

    async def test_delete_already_deleted_comment(
        self, authenticated_client: AsyncClient, test_session, test_user, test_post
    ):
        """已經刪除的留言不能再刪一次，刪除時間也不會被改寫"""
        deleted_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        comment = Comment(
            content="已刪除的評論",
            user_id=test_user.id,
            post_id=test_post.id,
            deleted_at=deleted_at
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        response = await authenticated_client.post(
            "/graphql",
            json={"query": DELETE_COMMENT_MUTATION, "variables": {"commentId": str(comment.id)}}
        )

        errors = response.json().get("errors")
        assert errors is not None
        assert errors[0]["message"] == "評論已被刪除"
        await test_session.refresh(comment)
        assert comment.deleted_at == deleted_at

    async def test_delete_comment_without_auth(
        self, client: AsyncClient, test_session, test_user, test_post
    ):
        """deleteComment 沒有掛 IsAuthenticated，未登入要由 resolver 擋下"""
        comment = Comment(
            content="評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add(comment)
        await test_session.commit()
        await test_session.refresh(comment)

        response = await client.post(
            "/graphql",
            json={"query": DELETE_COMMENT_MUTATION, "variables": {"commentId": str(comment.id)}}
        )

        errors = response.json().get("errors")
        assert errors is not None
        assert errors[0]["message"] == "需要登入才能刪除評論"
        await test_session.refresh(comment)
        assert comment.deleted_at is None


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
                    author { username }
                    post { id title }
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
        assert data["message"] == "評論已成功編輯"
        assert data["comment"]["content"] == "已編輯的內容"
        assert data["comment"]["author"] == {"username": test_user.username}
        assert data["comment"]["post"] == {"id": test_post.id, "title": test_post.title}
        # updated_at 應該被更新
        assert data["comment"]["updatedAt"] is not None

        # 用新的請求重新查詢，確認變更已寫入資料庫（未 commit 的變更會在請求結束時被丟棄）
        response = await authenticated_client.post(
            "/graphql",
            json={
                "query": "query GetPost($id: ID!) { post(id: $id) { comments { id content } } }",
                "variables": {"id": str(test_post.id)}
            }
        )
        comments = response.json()["data"]["post"]["comments"]
        assert comments == [{"id": str(comment.id), "content": "已編輯的內容"}]

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
        assert errors[0]["message"] == "評論內容不能為空"

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
        assert errors[0]["message"] == "沒有權限編輯此評論"

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
        assert errors[0]["message"] == "沒有權限編輯此評論"

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
            assert response.json()["errors"][0]["message"] == "評論內容不能為空"
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
        assert errors[0]["message"] == "評論不存在"

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
        assert errors[0]["message"] == "評論已被刪除"

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
        # 精確比對：錯誤訊息可能夾帶 SQL 參數（含送出的內容「未登入…」），用關鍵字比對會碰巧通過
        assert errors[0]["message"] == "需要登入才能編輯評論"