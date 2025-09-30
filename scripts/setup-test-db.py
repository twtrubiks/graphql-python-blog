#!/usr/bin/env python3

"""
測試資料庫設置腳本

這個腳本會自動創建測試資料庫 test_blog
如果資料庫已存在，會先刪除再重新創建

使用方式：
    python3 ../scripts/setup-test-db.py
"""

import asyncio
import sys
import asyncpg

# 資料庫連接配置
DB_HOST = "localhost"
DB_PORT = 5444
DB_USER = "blog_user"
DB_PASSWORD = "blog_password"
TEST_DB_NAME = "test_blog"


async def create_test_database():
    """創建測試資料庫"""

    # 連接到 postgres 資料庫（默認資料庫）
    conn = None
    try:
        print(f"🔌 連接到 PostgreSQL (host={DB_HOST}, port={DB_PORT})...")
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"  # 連接到默認資料庫
        )

        # 檢查測試資料庫是否存在
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
            TEST_DB_NAME
        )

        if exists:
            print(f"⚠️  測試資料庫 '{TEST_DB_NAME}' 已存在")

            # 終止所有連接到測試資料庫的會話
            print(f"🔧 終止所有連接到 '{TEST_DB_NAME}' 的會話...")
            await conn.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{TEST_DB_NAME}'
                AND pid <> pg_backend_pid()
            """)

            # 刪除現有的測試資料庫
            print(f"🗑️  刪除現有的測試資料庫 '{TEST_DB_NAME}'...")
            await conn.execute(f'DROP DATABASE IF EXISTS {TEST_DB_NAME}')

        # 創建新的測試資料庫
        print(f"✨ 創建新的測試資料庫 '{TEST_DB_NAME}'...")
        await conn.execute(f'CREATE DATABASE {TEST_DB_NAME}')

        print(f"✅ 測試資料庫 '{TEST_DB_NAME}' 創建成功！")

        # 顯示連接資訊
        print(f"\n📝 測試資料庫連接資訊：")
        print(f"   Host: {DB_HOST}")
        print(f"   Port: {DB_PORT}")
        print(f"   Database: {TEST_DB_NAME}")
        print(f"   User: {DB_USER}")
        print(f"   URL: postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}")

        return True

    except Exception as e:
        print(f"❌ 錯誤：{e}")
        return False

    finally:
        if conn:
            await conn.close()


async def verify_test_database():
    """驗證測試資料庫是否可以連接"""
    try:
        print(f"\n🔍 驗證測試資料庫連接...")
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=TEST_DB_NAME
        )

        # 測試查詢
        version = await conn.fetchval("SELECT version()")
        print(f"✅ 成功連接到測試資料庫")
        print(f"   PostgreSQL 版本：{version.split(',')[0]}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ 無法連接到測試資料庫：{e}")
        return False


async def main():
    """主函數"""
    print("🚀 開始設置測試資料庫...\n")

    # 創建測試資料庫
    success = await create_test_database()

    if success:
        # 驗證連接
        await verify_test_database()

        print("\n" + "="*60)
        print("🎉 測試資料庫設置完成！")
        print("   現在可以運行測試了：")
        print("   cd backend && pytest")
        print("="*60)
        return 0
    else:
        print("\n❌ 測試資料庫設置失敗")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)