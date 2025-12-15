"""Tag service for managing tags"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slugify import slugify

from app.models.tag import Tag


class TagService:
    @staticmethod
    async def get_or_create_tags(
        session: AsyncSession,
        tag_names: List[str]
    ) -> List[Tag]:
        """
        根據標籤名稱列表取得或創建標籤

        Args:
            session: 資料庫 session
            tag_names: 標籤名稱列表

        Returns:
            Tag 物件列表
        """
        if not tag_names:
            return []

        tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue

            slug = slugify(name)

            # 嘗試查找現有標籤
            result = await session.execute(
                select(Tag).where(Tag.slug == slug)
            )
            tag = result.scalar_one_or_none()

            if not tag:
                # 創建新標籤
                tag = Tag(name=name, slug=slug)
                session.add(tag)

            # 避免重複添加相同標籤
            if tag not in tags:
                tags.append(tag)

        return tags

    @staticmethod
    async def get_all_tags(session: AsyncSession) -> List[Tag]:
        """
        取得所有可用標籤

        Args:
            session: 資料庫 session

        Returns:
            所有標籤的列表，按名稱排序
        """
        result = await session.execute(
            select(Tag).order_by(Tag.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_tag_by_slug(session: AsyncSession, slug: str) -> Tag | None:
        """
        根據 slug 取得標籤

        Args:
            session: 資料庫 session
            slug: 標籤的 slug

        Returns:
            Tag 物件或 None
        """
        result = await session.execute(
            select(Tag).where(Tag.slug == slug)
        )
        return result.scalar_one_or_none()
