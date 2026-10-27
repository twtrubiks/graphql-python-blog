"""資料庫錯誤不能把 SQL、參數等內部細節回傳給客戶端"""
import logging

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.services.comment import CommentService
from app.services.like import LikeService
from app.services.post import PostService


SECRET_SQL = "INSERT INTO comments (content, user_id) VALUES ($1, $2)"


def database_error() -> IntegrityError:
    return IntegrityError(SECRET_SQL, ("secret parameter", 1), Exception("duplicate key value"))


def patch_to_fail(monkeypatch, service, method_name):
    async def fail(*args, **kwargs):
        raise database_error()

    monkeypatch.setattr(service, method_name, staticmethod(fail))


def assert_no_internal_details(message: str):
    for leaked in ("INSERT", "secret parameter", "duplicate key", "IntegrityError"):
        assert leaked not in message


@pytest.mark.asyncio
class TestMutationErrorMessages:
    """留言與按讚 mutation 遇到未預期的錯誤時，只回傳通用訊息"""

    @pytest.mark.parametrize("service, method_name, query, expected", [
        (CommentService, "create_comment",
         'mutation { addComment(postId: "1", content: "hi") { id } }', "創建評論失敗，請稍後再試"),
        (CommentService, "update_comment",
         'mutation { updateComment(commentId: "1", input: {content: "hi"}) { success } }', "編輯評論失敗，請稍後再試"),
        (CommentService, "delete_comment",
         'mutation { deleteComment(commentId: "1") { success } }', "刪除評論失敗，請稍後再試"),
        (LikeService, "like_post",
         'mutation { likePost(postId: "1") { success } }', "按讚失敗，請稍後再試"),
        (LikeService, "unlike_post",
         'mutation { unlikePost(postId: "1") { success } }', "取消按讚失敗，請稍後再試"),
    ], ids=["addComment", "updateComment", "deleteComment", "likePost", "unlikePost"])
    async def test_generic_message(
        self, authenticated_client: AsyncClient, monkeypatch, service, method_name, query, expected
    ):
        patch_to_fail(monkeypatch, service, method_name)

        response = await authenticated_client.post("/graphql", json={"query": query})

        data = response.json()
        assert data["data"] is None
        message = data["errors"][0]["message"]
        assert message == expected
        assert_no_internal_details(message)

    async def test_details_still_logged(self, authenticated_client: AsyncClient, monkeypatch, caplog):
        """客戶端看不到的細節要留在 server log，方便除錯"""
        patch_to_fail(monkeypatch, CommentService, "create_comment")

        with caplog.at_level(logging.ERROR):
            await authenticated_client.post(
                "/graphql",
                json={"query": 'mutation { addComment(postId: "1", content: "hi") { id } }'}
            )

        assert SECRET_SQL in caplog.text


@pytest.mark.asyncio
class TestUnhandledDatabaseErrors:
    """resolver 沒有攔下的資料庫錯誤，由 schema 的 MaskErrors 統一遮蔽"""

    async def test_database_error_is_masked(self, client: AsyncClient, monkeypatch, caplog):
        patch_to_fail(monkeypatch, PostService, "get_posts")

        with caplog.at_level(logging.ERROR):
            response = await client.post("/graphql", json={"query": "{ posts { edges { node { id } } } }"})

        data = response.json()
        assert data["data"] is None
        assert data["errors"][0]["message"] == "伺服器發生錯誤，請稍後再試"
        assert data["errors"][0]["path"] == ["posts"]
        assert SECRET_SQL in caplog.text

    async def test_other_errors_are_not_masked(self, client: AsyncClient):
        """預期中的錯誤（ValueError 等）照常回傳，前端才能顯示原因"""
        response = await client.post("/graphql", json={"query": "{ post { id } }"})

        assert response.json()["errors"][0]["message"] == "Either id or slug must be provided"
