import pytest
from httpx import AsyncClient
from app.models.like import Like
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestPostLikesQuery:
    """測試查詢文章按讚狀態"""
    
    async def test_get_post_likes_count(self, client: AsyncClient, test_session, test_post):
        """測試查詢文章按讚數"""
        # 創建多個用戶並按讚
        users = []
        for i in range(3):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                hashed_password=get_password_hash("password")
            )
            test_session.add(user)
            users.append(user)
        await test_session.commit()
        
        # 創建按讚
        for user in users:
            like = Like(user_id=user.id, post_id=test_post.id)
            test_session.add(like)
        await test_session.commit()
        
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
                likesCount
            }
        }
        """
        
        variables = {"id": str(test_post.id)}
        
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["post"]
        assert data["likesCount"] == 3
    
    async def test_get_post_is_liked_authenticated(self, authenticated_client: AsyncClient, test_session, test_user, test_post):
        """測試登入用戶查詢文章是否按讚"""
        # 創建按讚
        like = Like(user_id=test_user.id, post_id=test_post.id)
        test_session.add(like)
        await test_session.commit()
        
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
                isLiked
                likesCount
            }
        }
        """
        
        variables = {"id": str(test_post.id)}
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["post"]
        assert data["isLiked"] is True
        assert data["likesCount"] == 1
    
    async def test_get_post_is_liked_not_liked(self, authenticated_client: AsyncClient, test_post):
        """測試登入用戶查詢未按讚的文章"""
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
                isLiked
                likesCount
            }
        }
        """
        
        variables = {"id": str(test_post.id)}
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["post"]
        assert data["isLiked"] is False
        assert data["likesCount"] == 0
    
    async def test_get_post_is_liked_unauthenticated(self, client: AsyncClient, test_session, test_user, test_post):
        """測試未登入用戶查詢文章按讚狀態"""
        # 創建按讚
        like = Like(user_id=test_user.id, post_id=test_post.id)
        test_session.add(like)
        await test_session.commit()
        
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
                isLiked
                likesCount
            }
        }
        """
        
        variables = {"id": str(test_post.id)}
        
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["post"]
        assert data["isLiked"] is False  # 未登入永遠返回 False
        assert data["likesCount"] == 1  # 但按讚數是正確的
    
    async def test_multiple_posts_likes_status(self, authenticated_client: AsyncClient, test_session, test_user):
        """測試查詢多篇文章的按讚狀態"""
        # 創建多篇文章
        from app.models.post import Post, PostStatus
        
        posts = []
        for i in range(3):
            post = Post(
                title=f"Post {i}",
                slug=f"post-{i}",
                content=f"Content {i}",
                status=PostStatus.PUBLISHED,
                author_id=test_user.id
            )
            test_session.add(post)
            posts.append(post)
        await test_session.commit()
        
        # 只按讚第一篇和第三篇
        like1 = Like(user_id=test_user.id, post_id=posts[0].id)
        like3 = Like(user_id=test_user.id, post_id=posts[2].id)
        test_session.add_all([like1, like3])
        await test_session.commit()
        
        query = """
        query GetPosts {
            posts(limit: 10) {
                edges {
                    node {
                        id
                        title
                        isLiked
                        likesCount
                    }
                }
            }
        }
        """
        
        response = await authenticated_client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        edges = response.json()["data"]["posts"]["edges"]
        
        # 找到我們創建的文章
        our_posts = [edge["node"] for edge in edges if edge["node"]["title"].startswith("Post ")]
        assert len(our_posts) >= 3
        
        # 檢查按讚狀態
        liked_posts = [p for p in our_posts if p["isLiked"]]
        assert len(liked_posts) == 2  # 應該有兩篇被按讚