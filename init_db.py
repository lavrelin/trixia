#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import Config
from models import Base, User, Post, Gender, PostStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize database tables"""
    try:
        db_url = Config.DATABASE_URL
        
        logger.info(f"🔍 DATABASE_URL (first 50 chars): {db_url[:50]}...")
        
        if not db_url:
            logger.error("❌ DATABASE_URL is empty!")
            return False
        
        # Конвертируем URL для async
        if db_url.startswith('sqlite'):
            if not db_url.startswith('sqlite+aiosqlite'):
                db_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
            logger.info("📊 Using SQLite with aiosqlite")
        elif db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql+asyncpg://', 1)
            logger.info("📊 Using PostgreSQL with asyncpg")
        elif db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
            logger.info("📊 Using PostgreSQL with asyncpg")
        elif db_url.startswith('mysql'):
            # НОВОЕ: поддержка MySQL (на случай если Railway предоставит)
            db_url = db_url.replace('mysql://', 'mysql+aiomysql://', 1)
            logger.info("📊 Using MySQL with aiomysql")
        else:
            logger.warning(f"⚠️ Unknown database type: {db_url[:30]}...")
        
        logger.info(f"✅ Converted URL (first 50 chars): {db_url[:50]}...")
        
        # ИСПРАВЛЕНИЕ: добавляем таймауты для подключения
        logger.info("🔄 Creating async engine...")
        
        engine = create_async_engine(
            db_url,
            echo=False,  # ИСПРАВЛЕНИЕ: echo=False для чистоты логов
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={
                'timeout': 30,  # НОВОЕ: таймаут для SQLite
                'ssl': 'prefer' if 'postgresql' in db_url else None,  # SSL для PostgreSQL
            }
        )
        
        logger.info("⏳ Testing connection...")
        
        # ИСПРАВЛЕНИЕ: тестируем подключение перед созданием таблиц
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Connection test successful")
        except Exception as conn_error:
            logger.error(f"❌ Connection test failed: {conn_error}")
            logger.error(f"DATABASE_URL: {db_url[:50]}...")
            raise
        
        # Создаем все таблицы
        logger.info("🔄 Creating tables from Base.metadata...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
        
        # Проверяем созданные таблицы
        async with engine.connect() as conn:
            if 'postgresql' in db_url:
                result = await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
                )
            elif 'mysql' in db_url:
                result = await conn.execute(
                    text("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME")
                )
            else:
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                )
            
            tables = [row[0] for row in result]
            logger.info(f"✅ Tables in database: {tables}")
            
            if 'users' not in tables:
                logger.error("❌ Table 'users' not found!")
                return False
            if 'posts' not in tables:
                logger.error("❌ Table 'posts' not found!")
                return False
        
        await engine.dispose()
        logger.info("✅ Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(init_database())
        if success:
            print("\n✅ SUCCESS: Database initialized properly")
            exit(0)
        else:
            print("\n❌ FAILED: Database initialization failed")
            exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
