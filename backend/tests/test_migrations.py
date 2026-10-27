"""
alembic migration 建出的資料表要和 models 完全一致

測試資料庫是用 Base.metadata.create_all() 依 models 建表，正式環境則是跑 alembic migration。
兩者不一致時（例如 model 加了 unique、改了 nullable 卻沒有寫 migration），
測試通過不代表正式環境的資料庫有同樣的約束。
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import asyncpg
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.models import comment, follow, like, post, tag, user  # noqa: F401  讓 Base.metadata 包含所有資料表

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATION_DB = f"{settings.TEST_DB_NAME}_migrations"


async def admin_execute(sql: str):
    conn = await asyncpg.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USER, password=settings.DB_PASSWORD, database="postgres",
    )
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def schema_differences():
    engine = create_async_engine(
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{MIGRATION_DB}"
    )
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(
                lambda sync_conn: compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)
            )
    finally:
        await engine.dispose()


def migrate_and_compare(monkeypatch):
    asyncio.run(admin_execute(f"DROP DATABASE IF EXISTS {MIGRATION_DB}"))
    asyncio.run(admin_execute(f"CREATE DATABASE {MIGRATION_DB}"))
    try:
        monkeypatch.setattr(settings, "DB_NAME", MIGRATION_DB)  # alembic/env.py 由 settings 組出連線字串
        config = Config()  # 不讀 alembic.ini：它的 logging 設定會停用其他 logger
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(config, "head")
        return asyncio.run(schema_differences())
    finally:
        asyncio.run(admin_execute(f"DROP DATABASE IF EXISTS {MIGRATION_DB}"))


def test_migrations_match_models(monkeypatch):
    # alembic/env.py 會自己呼叫 asyncio.run()，放到另一個執行緒，不影響測試的事件迴圈
    with ThreadPoolExecutor(max_workers=1) as executor:
        differences = executor.submit(migrate_and_compare, monkeypatch).result()

    assert differences == []
