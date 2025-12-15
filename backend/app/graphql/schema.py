"""
GraphQL Schema 定義 - API 的核心

這個檔案定義了整個 GraphQL API 的結構，包含：
- Query: 資料查詢操作（讀取）
- Mutation: 資料變更操作（創建、更新、刪除）
- Subscription: 即時資料訂閱（WebSocket）

GraphQL 的優勢：
1. 客戶端可以精確指定需要的資料
2. 單一端點，減少網路請求
3. 強型別系統，自動生成文檔
4. 解決過度獲取和不足獲取問題

教學重點：
- 使用 Strawberry 的裝飾器定義 Schema
- 權限控制透過 permission_classes 實現
- 使用繼承組織複雜的 Query/Mutation
"""

import strawberry
from typing import Optional, List
from app.graphql.mutations.auth import register, login, AuthPayload
from app.graphql.mutations.post import (
    create_post,
    update_post,
    delete_post,
    publish_post,
    unpublish_post,
    DeletePostResult
)
from app.graphql.mutations.comment import CommentMutation
from app.graphql.mutations.like import LikeMutation
from app.graphql.mutations.follow import FollowMutation
from app.graphql.queries.auth import me, protected_data, ProtectedData
from app.graphql.queries.user import get_user, get_users
from app.graphql.queries.post import PostQuery
from app.graphql.queries.search import SearchQuery
from app.graphql.queries.tag import TagQuery
from app.graphql.types.user import UserType
from app.graphql.types.post import PostType
from app.graphql.subscriptions.comment import CommentSubscription
from app.graphql.subscriptions.user_status import UserStatusSubscription
from app.graphql.subscriptions.post import PostSubscription
from app.graphql.subscriptions.followed_user_post import FollowedUserPostSubscription
from app.graphql.subscriptions.post_deleted import PostDeletedSubscription
from app.graphql.permissions import IsAuthenticated


@strawberry.type
class Query(PostQuery, SearchQuery, TagQuery):
    """
    Query Type - 定義所有查詢操作

    透過繼承 PostQuery、SearchQuery 和 TagQuery 來組織複雜的查詢，
    保持程式碼模組化和可維護性。
    """

    @strawberry.field
    def hello(self, name: Optional[str] = None) -> str:
        """簡單的測試查詢，用於驗證 GraphQL 服務是否正常運行"""
        return f"Hello {name or 'World'}!"

    @strawberry.field
    def version(self) -> str:
        """返回 API 版本號"""
        return "1.0.0"

    # 認證相關查詢
    me: Optional[UserType] = strawberry.field(
        resolver=me,
        permission_classes=[IsAuthenticated]  # 需要認證才能訪問
    )
    protectedData: ProtectedData = strawberry.field(
        resolver=protected_data,
        name="protectedData",
        permission_classes=[IsAuthenticated]
    )
    user: Optional[UserType] = strawberry.field(resolver=get_user)
    users: List[UserType] = strawberry.field(resolver=get_users)


@strawberry.type
class Mutation(CommentMutation, LikeMutation, FollowMutation):
    """
    Mutation Type - 定義所有變更操作

    GraphQL 的設計原則：
    - Query 用於讀取資料（不應有副作用）
    - Mutation 用於變更資料（創建、更新、刪除）

    透過繼承來組織相關的 Mutation，提高程式碼重用性。
    """

    # 認證相關 Mutations（公開，不需要認證）
    register: AuthPayload = strawberry.field(resolver=register)
    login: AuthPayload = strawberry.field(resolver=login)

    # 文章相關 Mutations（需要認證）
    create_post: PostType = strawberry.field(
        resolver=create_post,
        permission_classes=[IsAuthenticated]  # 使用裝飾器模式實現權限控制
    )
    update_post: PostType = strawberry.field(
        resolver=update_post,
        permission_classes=[IsAuthenticated]
    )
    delete_post: DeletePostResult = strawberry.field(
        resolver=delete_post,
        permission_classes=[IsAuthenticated]
    )
    publish_post: PostType = strawberry.field(
        resolver=publish_post,
        permission_classes=[IsAuthenticated]
    )
    unpublish_post: PostType = strawberry.field(
        resolver=unpublish_post,
        permission_classes=[IsAuthenticated]
    )

    @strawberry.mutation
    def echo(self, message: str) -> str:
        return f"Echo: {message}"


@strawberry.type
class Subscription(CommentSubscription, UserStatusSubscription, PostSubscription, FollowedUserPostSubscription, PostDeletedSubscription):
    """
    Subscription Type - 定義即時訂閱操作

    Subscription 是 GraphQL 的第三種操作類型，用於即時資料推送。
    使用 WebSocket 協議，讓客戶端可以訂閱資料變化。

    應用場景：
    - 即時聊天訊息
    - 新文章發布通知（全域）
    - 追蹤用戶發文通知（個人化）
    - 文章刪除通知（追蹤者）
    - 用戶狀態變更
    - 即時協作編輯

    透過繼承整合不同的訂閱功能，保持程式碼組織性。
    """
    pass


# 創建 GraphQL Schema - 這是整個 API 的入口點
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

"""
Schema 是 GraphQL 的核心，定義了：
1. 可用的操作類型（Query, Mutation, Subscription）
2. 每個操作的輸入和輸出類型
3. 欄位之間的關係

Strawberry 會自動：
- 生成 GraphQL Schema 文檔
- 提供 GraphiQL 測試介面
- 進行類型檢查和驗證
- 處理錯誤和異常
"""