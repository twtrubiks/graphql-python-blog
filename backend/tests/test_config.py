"""設定檔解析：CORS_ORIGINS 的環境變數可以用逗號分隔或 JSON 陣列"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

ORIGINS = ["http://a.example.com", "http://b.example.com"]


@pytest.mark.parametrize("value", [
    "http://a.example.com, http://b.example.com",
    '["http://a.example.com", "http://b.example.com"]',
], ids=["comma-separated", "json"])
def test_cors_origins_from_environment(monkeypatch, value):
    monkeypatch.setenv("CORS_ORIGINS", value)

    assert Settings(_env_file=None).CORS_ORIGINS == ORIGINS


def test_cors_origins_from_list():
    assert Settings(_env_file=None, CORS_ORIGINS=ORIGINS).CORS_ORIGINS == ORIGINS


def test_cors_origins_rejects_other_types():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, CORS_ORIGINS=123)


def test_database_url_follows_db_settings():
    settings = Settings(_env_file=None, DB_USER="u", DB_PASSWORD="p", DB_HOST="db", DB_PORT=6543, DB_NAME="blog")

    assert settings.DATABASE_URL == "postgresql://u:p@db:6543/blog"
