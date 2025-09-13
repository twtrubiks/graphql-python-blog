import pytest
from httpx import AsyncClient
from app.models.comment import Comment
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
class TestPostCommentsQuery:
    """測試查詢文章評論"""
    
    async def test_get_post_comments(self, client: AsyncClient, test_session, test_user, test_post):
        """測試查詢文章的所有評論"""
        # 創建多個評論
        comment1 = Comment(
            content="第一個評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        comment2 = Comment(
            content="第二個評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        test_session.add_all([comment1, comment2])
        await test_session.commit()
        
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
                    createdAt
                }
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
        
        assert len(data["comments"]) == 2
        assert any(c["content"] == "第一個評論" for c in data["comments"])
        assert any(c["content"] == "第二個評論" for c in data["comments"])
        assert all(c["author"]["username"] == "testuser" for c in data["comments"])
    
    async def test_comments_exclude_deleted(self, client: AsyncClient, test_session, test_user, test_post):
        """測試查詢評論時排除已刪除的評論"""
        # 創建正常評論
        comment1 = Comment(
            content="正常評論",
            user_id=test_user.id,
            post_id=test_post.id
        )
        # 創建已刪除評論
        comment2 = Comment(
            content="已刪除評論",
            user_id=test_user.id,
            post_id=test_post.id,
            deleted_at=datetime.now(timezone.utc)
        )
        test_session.add_all([comment1, comment2])
        await test_session.commit()
        
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                comments {
                    id
                    content
                }
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
        
        # 應該只返回未刪除的評論
        assert len(data["comments"]) == 1
        assert data["comments"][0]["content"] == "正常評論"
    
    async def test_comments_sorted_by_creation(self, client: AsyncClient, test_session, test_user, test_post):
        """測試評論按創建時間排序"""
        base_time = datetime.now(timezone.utc)
        
        # 創建不同時間的評論
        comment1 = Comment(
            content="最新評論",
            user_id=test_user.id,
            post_id=test_post.id,
            created_at=base_time
        )
        comment2 = Comment(
            content="較早評論",
            user_id=test_user.id,
            post_id=test_post.id,
            created_at=base_time - timedelta(hours=1)
        )
        comment3 = Comment(
            content="最早評論",
            user_id=test_user.id,
            post_id=test_post.id,
            created_at=base_time - timedelta(hours=2)
        )
        test_session.add_all([comment1, comment2, comment3])
        await test_session.commit()
        
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                comments {
                    content
                    createdAt
                }
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
        comments = data["comments"]
        
        # 評論應該按時間順序排列（最早的在前）
        assert len(comments) == 3
        assert comments[0]["content"] == "最早評論"
        assert comments[1]["content"] == "較早評論"
        assert comments[2]["content"] == "最新評論"
    
    async def test_empty_comments_list(self, client: AsyncClient, test_post):
        """測試沒有評論時返回空列表"""
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                title
                comments {
                    id
                    content
                }
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
        
        assert data["comments"] == []
    
    async def test_comments_with_pagination(self, client: AsyncClient, test_session, test_user, test_post):
        """測試評論分頁查詢"""
        # 創建多個評論
        for i in range(10):
            comment = Comment(
                content=f"評論 {i+1}",
                user_id=test_user.id,
                post_id=test_post.id
            )
            test_session.add(comment)
        await test_session.commit()
        
        query = """
        query GetPost($id: ID!, $limit: Int, $offset: Int) {
            post(id: $id) {
                id
                comments(limit: $limit, offset: $offset) {
                    id
                    content
                }
                totalComments
            }
        }
        """
        
        # 測試第一頁
        variables = {"id": str(test_post.id), "limit": 5, "offset": 0}
        
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["post"]
        
        assert len(data["comments"]) == 5
        assert data["totalComments"] == 10
        
        # 測試第二頁
        variables = {"id": str(test_post.id), "limit": 5, "offset": 5}
        
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]["post"]
        
        assert len(data["comments"]) == 5
        assert data["totalComments"] == 10