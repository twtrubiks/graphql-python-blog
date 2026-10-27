"""TagService.get_or_create_tags：沿用既有標籤、建立新標籤，slug 相同的只算一個"""
import pytest

from app.models.tag import Tag
from app.services.tag import TagService


@pytest.mark.asyncio
async def test_get_or_create_tags(test_session):
    test_session.add(Tag(name="python", slug="python"))
    await test_session.commit()

    tags = await TagService.get_or_create_tags(test_session, ["Python", "  GraphQL  ", "", "graphql"])
    await test_session.commit()  # 新標籤還沒掛到任何文章上，也要被 add 進 session 才會寫入

    assert [(tag.name, tag.slug) for tag in tags] == [("python", "python"), ("GraphQL", "graphql")]
    saved = await TagService.get_all_tags(test_session)
    assert [(tag.name, tag.slug) for tag in saved] == [("GraphQL", "graphql"), ("python", "python")]


@pytest.mark.asyncio
async def test_get_or_create_tags_without_names(test_session):
    assert await TagService.get_or_create_tags(test_session, []) == []
