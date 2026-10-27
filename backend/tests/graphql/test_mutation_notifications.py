"""Mutation 成功後要推播給訂閱者（commentAdded、postPublished、followedUserPosted、postDeleted）"""
import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.graphql.mutations.post import _background_tasks, _run_in_background
from app.graphql.subscriptions.comment import CommentEvent
from app.graphql.subscriptions.followed_user_post import FollowedUserPostEvent
from app.graphql.subscriptions.post import PostEvent
from app.graphql.subscriptions.post_deleted import PostDeletedEvent
from app.models.follow import Follow
from app.models.post import Post, PostStatus


ADD_COMMENT_MUTATION = """
mutation AddComment($postId: ID!, $content: String!) {
    addComment(postId: $postId, content: $content) { id }
}
"""

CREATE_POST_MUTATION = """
mutation CreatePost($input: PostInput!) {
    createPost(input: $input) { id }
}
"""

UPDATE_POST_MUTATION = """
mutation UpdatePost($id: ID!, $input: UpdatePostInput!) {
    updatePost(id: $id, input: $input) { id }
}
"""

DELETE_POST_MUTATION = """
mutation DeletePost($id: ID!) {
    deletePost(id: $id) { success }
}
"""


async def mutate(client: AsyncClient, query: str, **variables) -> dict:
    response = await client.post("/graphql", json={"query": query, "variables": variables})
    data = response.json()
    assert "errors" not in data, data["errors"]
    return data["data"]


async def create_post(client: AsyncClient, title: str, status: str) -> str:
    data = await mutate(
        client, CREATE_POST_MUTATION, input={"title": title, "content": "content", "status": status}
    )
    return data["createPost"]["id"]


async def follow_author(test_session: AsyncSession, author, user_factory):
    follower = await user_factory.create()
    test_session.add(Follow(follower_id=follower.id, followed_id=author.id))
    await test_session.commit()
    return follower


@pytest.mark.asyncio
class TestCommentAddedNotification:
    async def test_add_comment_publishes_event(self, authenticated_client: AsyncClient, test_user, test_post):
        post_id = str(test_post.id)
        queue = CommentEvent.subscribe(post_id)
        try:
            response = await authenticated_client.post(
                "/graphql",
                json={"query": ADD_COMMENT_MUTATION, "variables": {"postId": post_id, "content": "第一則留言"}}
            )
            comment_id = response.json()["data"]["addComment"]["id"]

            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert event.id == comment_id
            assert event.content == "第一則留言"
            assert event.author.username == test_user.username
        finally:
            CommentEvent.unsubscribe(post_id, queue)

    async def test_failed_add_comment_does_not_publish(self, authenticated_client: AsyncClient, test_post):
        post_id = str(test_post.id)
        queue = CommentEvent.subscribe(post_id)
        try:
            response = await authenticated_client.post(
                "/graphql",
                json={"query": ADD_COMMENT_MUTATION, "variables": {"postId": post_id, "content": "   "}}
            )

            assert response.json()["errors"][0]["message"] == "評論內容不能為空"
            assert queue.empty()
        finally:
            CommentEvent.unsubscribe(post_id, queue)


@pytest.mark.asyncio
class TestCreatePostNotification:
    """以 PUBLISHED 狀態建立文章，等同發布，要通知所有訂閱者與作者的追蹤者"""

    async def test_published_post_notifies_subscribers(self, authenticated_client: AsyncClient):
        queue = PostEvent.subscribe()
        try:
            # 草稿不通知：下一個收到的事件必須是之後發布的那篇
            await create_post(authenticated_client, "草稿", "DRAFT")
            post_id = await create_post(authenticated_client, "直接發布", "PUBLISHED")

            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert event.id == int(post_id)
            assert event.title == "直接發布"
        finally:
            PostEvent.unsubscribe(queue)

    async def test_published_post_notifies_followers_only(
        self, authenticated_client: AsyncClient, test_session: AsyncSession, test_user, user_factory
    ):
        """追蹤者由背景工作另開 session 查詢；能收到通知，代表它查的是測試資料庫"""
        follower = await follow_author(test_session, test_user, user_factory)
        stranger = await user_factory.create()

        follower_queue = FollowedUserPostEvent.subscribe(follower.id)
        stranger_queue = FollowedUserPostEvent.subscribe(stranger.id)
        try:
            await create_post(authenticated_client, "草稿", "DRAFT")
            post_id = await create_post(authenticated_client, "直接發布", "PUBLISHED")

            event = await asyncio.wait_for(follower_queue.get(), timeout=2.0)
            assert event.id == int(post_id)
            assert stranger_queue.empty()
        finally:
            FollowedUserPostEvent.unsubscribe(follower.id, follower_queue)
            FollowedUserPostEvent.unsubscribe(stranger.id, stranger_queue)


@pytest.mark.asyncio
class TestPublishPostNotification:
    async def test_publish_post_notifies_followers(
        self, authenticated_client: AsyncClient, test_session: AsyncSession, test_user, user_factory
    ):
        follower = await follow_author(test_session, test_user, user_factory)
        post_id = await create_post(authenticated_client, "待發布", "DRAFT")

        queue = FollowedUserPostEvent.subscribe(follower.id)
        try:
            await mutate(authenticated_client, "mutation P($id: ID!) { publishPost(id: $id) { id } }", id=post_id)

            event = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert event.id == int(post_id)
            assert event.title == "待發布"
        finally:
            FollowedUserPostEvent.unsubscribe(follower.id, queue)


@pytest.mark.asyncio
class TestDeletePostNotification:
    async def test_delete_post_notifies_followers_only(
        self, authenticated_client: AsyncClient, test_session: AsyncSession, test_user, user_factory
    ):
        follower = await follow_author(test_session, test_user, user_factory)
        stranger = await user_factory.create()
        post_id = await create_post(authenticated_client, "待刪除", "DRAFT")

        follower_queue = PostDeletedEvent.subscribe(follower.id)
        stranger_queue = PostDeletedEvent.subscribe(stranger.id)
        try:
            data = await mutate(authenticated_client, DELETE_POST_MUTATION, id=post_id)
            assert data["deletePost"]["success"] is True

            assert await asyncio.wait_for(follower_queue.get(), timeout=1.0) == int(post_id)
            assert stranger_queue.empty()
        finally:
            PostDeletedEvent.unsubscribe(follower.id, follower_queue)
            PostDeletedEvent.unsubscribe(stranger.id, stranger_queue)


@pytest.mark.asyncio
async def test_background_task_kept_until_done():
    """event loop 只保留 task 的弱參考，執行完之前要由 _background_tasks 保留"""
    release = asyncio.Event()
    task = _run_in_background(release.wait())
    assert task in _background_tasks

    release.set()
    await task
    await asyncio.sleep(0)  # done callback 由 event loop 排程執行
    assert task not in _background_tasks
