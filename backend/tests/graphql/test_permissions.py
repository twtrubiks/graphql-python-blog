"""權限類別直接回傳布林值（宣告為 -> bool），不靠 None 的 falsy 行為"""
from types import SimpleNamespace

import pytest

import app.core.auth as core_auth
import app.graphql.permissions as permissions
from app.core.auth import require_auth
from app.graphql.permissions import IsAuthenticated, IsOwnerOrSuperuser

OWNER = SimpleNamespace(id=1, is_superuser=False)
OTHER = SimpleNamespace(id=2, is_superuser=False)
ADMIN = SimpleNamespace(id=3, is_superuser=True)


def login_as(monkeypatch, user):
    async def current_user(info):
        return user

    monkeypatch.setattr(permissions, "get_current_user", current_user)


@pytest.mark.asyncio
@pytest.mark.parametrize("viewer, expected", [(None, False), (OTHER, True)])
async def test_is_authenticated(monkeypatch, viewer, expected):
    login_as(monkeypatch, viewer)

    assert await IsAuthenticated().has_permission(source=None, info=None) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("viewer, expected", [
    (None, False),
    (OTHER, False),
    (OWNER, True),
    (ADMIN, True),
], ids=["anonymous", "other", "owner", "superuser"])
async def test_is_owner_or_superuser(monkeypatch, viewer, expected):
    login_as(monkeypatch, viewer)
    source = SimpleNamespace(id="1")  # UserType 的 id 是字串

    assert await IsOwnerOrSuperuser().has_permission(source=source, info=None) is expected


@pytest.mark.asyncio
async def test_is_owner_or_superuser_without_source_id(monkeypatch):
    login_as(monkeypatch, OWNER)

    assert await IsOwnerOrSuperuser().has_permission(source=object(), info=None) is False


@pytest.mark.asyncio
async def test_require_auth(monkeypatch):
    """resolver 內的第二道檢查：即使欄位沒有掛 IsAuthenticated，也不能讓未登入的請求通過"""
    async def current_user(info):
        return user

    monkeypatch.setattr(core_auth, "get_current_user", current_user)

    user = None
    with pytest.raises(ValueError, match="^Authentication required$"):
        await require_auth(info=None)

    user = OWNER
    assert await require_auth(info=None) is OWNER

