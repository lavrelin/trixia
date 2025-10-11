#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize database tables"""
    try:
        # ИСПРАВЛЕНИЕ: Правильное получение DATABASE_URL
        db_url = os.getenv("DATABASE_URL")
        
        logger.info("=" * 60)
        logger.info("🔍 DATABASE INITIALIZATION")
        logger.info("=" * 60)
        
        if not db_url:
            logger.warning("⚠️  DATABASE_URL is not set")
            logger.info("💡 Possible causes:")
            logger.info("  1. PostgreSQL service not created in Railway")
            logger.info("  2. Variable not linked to project")
            logger.info("  3. Project hasn't redeployed after PostgreSQL creation")
            logger.info("")
            logger.info("📋 Available environment variables:")
            for key in sorted(os.environ.keys()):
                if 'DB' in key or 'DATABASE' in key or 'POSTGRES' in key:
                    logger.info(f"  {key}={os.environ[key][:50]}...")
            
            # ИСПРАВЛЕНИЕ: SQLite fallback для локального тестирования
            logger.warning("⚠️  Using SQLite fallback for local testing")
            db_url = "sqlite+aiosqlite:///./trixbot.db"
        
        logger.info(f"✅ DATABASE_URL (first 60 chars): {db_url[:60]}...")
        logger.info("")
        
        # Определяем тип БД
        if 'sqlite' in db_url:
            db_type = "SQLite"
            db_url_for_display = db_url
        elif 'postgresql' in db_url or 'postgres' in db_url:
            db_type = "PostgreSQL"
            # Скрываем пароль в логах
            if '@' in db_url:
                parts = db_url.split('@')
                db_url_for_display = f"{parts[0][:30]}...@{parts[1]}"
            else:
                db_url_for_display = db_url[:60]
        else:
            db_type = "Unknown"
            db_url_for_display = db_url[:60]
        
        logger.info(f"📊 Database Type: {db_type}")
        logger.info(f"📊 Connection String: {db_url_for_display}...")
        logger.info("")
        
        # ИСПРАВЛЕНИЕ: Конвертируем URL если нужно
        if db_url.startswith('postgresql://') and 'asyncpg' not in db_url:
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
            logger.info("🔄 Converted postgresql:// to postgresql+asyncpg://")
        elif db_url.startswith('postgres://') and 'asyncpg' not in db_url:
            db_url = db_url.replace('postgres://', 'postgresql+asyncpg://', 1)
            logger.info("🔄 Converted postgres:// to postgresql+asyncpg://")
        
        logger.info("")
        logger.info("🔄 Creating async engine...")
        
        try:
            engine = create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                connect_args={
                    'timeout': 30 if 'sqlite' in db_url else None,
                    'ssl': 'require' if 'postgresql' in db_url else None,
                    'command_timeout': 60 if 'postgresql' in db_url else None,
                } if 'sqlite' in db_url or 'postgresql' in db_url else {}
            )
            logger.info("✅ Engine created successfully")
        except Exception as engine_error:
            logger.error(f"❌ Failed to create engine: {engine_error}")
            raise
        
        logger.info("")
        logger.info("⏳ Testing database connection (timeout: 30s)...")
        
        try:
            # ИСПРАВЛЕНИЕ: Таймаут для тестового подключения
            async with asyncio.timeout(30):
                async with engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    value = result.scalar()
                    logger.info(f"✅ Connection test successful (result: {value})")
        except asyncio.TimeoutError:
            logger.error("❌ Connection test timeout (30s)")
            logger.error("💡 Possible causes:")
            logger.error("  1. Database server is not running")
            logger.error("  2. Network connectivity issue")
            logger.error("  3. Firewall blocking connection")
            raise
        except Exception as conn_error:
            logger.error(f"❌ Connection test failed: {conn_error}")
            logger.error(f"   Error type: {type(conn_error).__name__}")
            logger.error(f"   Error message: {str(conn_error)[:200]}")
            raise
        
        logger.info("")
        logger.info("🔄 Creating database tables...")
        
        try:
            from models import Base
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Database tables created successfully")
        except Exception as create_error:
            logger.error(f"❌ Failed to create tables: {create_error}")
            raise
        
        logger.info("")
        logger.info("✅ Verifying tables...")
        
        try:
            async with engine.connect() as conn:
                if 'postgresql' in db_url:
                    logger.info("📊 Querying PostgreSQL tables...")
                    result = await conn.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
                    )
                elif 'mysql' in db_url:
                    logger.info("📊 Querying MySQL tables...")
                    result = await conn.execute(
                        text("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME")
                    )
                else:
                    logger.info("📊 Querying SQLite tables...")
                    result = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                    )
                
                tables = [row[0] for row in result.fetchall()]
                logger.info(f"✅ Tables found: {tables}")
                
                required_tables = {'users', 'posts'}
                missing_tables = required_tables - set(tables)
                
                if missing_tables:
                    logger.error(f"❌ Missing required tables: {missing_tables}")
                    return False
                
                logger.info("✅ All required tables are present")
        except Exception as verify_error:
            logger.error(f"❌ Failed to verify tables: {verify_error}")
            raise
        
        logger.info("")
        await engine.dispose()
        logger.info("✅ Database initialization completed successfully")
        logger.info("=" * 60)
        return True
        
    except asyncio.TimeoutError:
        logger.error("❌ Operation timeout")
        logger.error("💡 Try again or check Railway PostgreSQL status")
        return False
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ CRITICAL ERROR DURING DATABASE INITIALIZATION")
        logger.error("=" * 60)
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Error Message: {str(e)}")
        logger.error("")
        logger.error("🔍 Debugging information:")
        logger.error(f"  DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")
        logger.error(f"  BOT_TOKEN set: {bool(os.getenv('BOT_TOKEN'))}")
        logger.error("")
        logger.error("💡 Common solutions:")
        logger.error("  1. Ensure PostgreSQL is created in Railway")
        logger.error("  2. Check PROJECT_ID environment variable")
        logger.error("  3. Restart the Railway deployment")
        logger.error("  4. Check Railway logs for more details")
        logger.error("=" * 60)
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(init_database())
        if success:
            print("\n" + "=" * 60)
            print("✅ SUCCESS: Database ready for use")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ FAILED: Database initialization failed")
            print("=" * 60)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Database initialization interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
