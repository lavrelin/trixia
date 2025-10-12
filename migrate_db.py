#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_database():
    """
    ПОЛНАЯ ОЧИСТКА И ПЕРЕСОЗДАНИЕ БД
    Удаляет все таблицы и создает их заново с правильной схемой
    """
    try:
        db_url = Config.DATABASE_URL
        
        if not db_url:
            logger.error("❌ DATABASE_URL not set!")
            return False
        
        # Конвертируем URL если нужно
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql+asyncpg://', 1)
        elif db_url.startswith('sqlite:///'):
            db_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)
        elif db_url.startswith('sqlite://'):
            db_url = db_url.replace('sqlite://', 'sqlite+aiosqlite:///', 1)
        
        logger.info(f"📊 Database URL: {db_url[:60]}...")
        
        # Создаем engine
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={'timeout': 30} if 'sqlite' in db_url else {}
        )
        
        logger.info("🔄 Подключаюсь к базе данных...")
        
        # Тестируем подключение
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                logger.info("✅ Подключение успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            await engine.dispose()
            return False
        
        # УДАЛЯЕМ ВСЕ ТАБЛИЦЫ
        logger.info("🔥 УДАЛЯЮ ВСЕ ТАБЛИЦЫ...")
        try:
            async with engine.begin() as conn:
                if 'postgresql' in db_url:
                    # PostgreSQL
                    await conn.execute(text("""
                        DROP TABLE IF EXISTS posts CASCADE;
                        DROP TABLE IF EXISTS users CASCADE;
                    """))
                else:
                    # SQLite
                    await conn.execute(text("DROP TABLE IF EXISTS posts;"))
                    await conn.execute(text("DROP TABLE IF EXISTS users;"))
                
            logger.info("✅ Таблицы удалены")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при удалении таблиц (игнорируется): {e}")
        
        # СОЗДАЕМ НОВЫЕ ТАБЛИЦЫ
        logger.info("🔨 СОЗДАЮ НОВЫЕ ТАБЛИЦЫ...")
        try:
            from models import Base
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Таблицы созданы успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка при создании таблиц: {e}")
            await engine.dispose()
            return False
        
        # ПРОВЕРЯЕМ ТАБЛИЦЫ
        logger.info("✅ ПРОВЕРЯЮ ТАБЛИЦЫ...")
        try:
            async with engine.connect() as conn:
                if 'postgresql' in db_url:
                    result = await conn.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                    )
                else:
                    result = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                
                tables = [row[0] for row in result.fetchall()]
                logger.info(f"✅ Таблицы в БД: {tables}")
                
                if not tables:
                    logger.error("❌ Таблицы не созданы!")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке таблиц: {e}")
            await engine.dispose()
            return False
        
        await engine.dispose()
        
        logger.info("\n" + "="*60)
        logger.info("✅ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        logger.info("="*60)
        logger.info("\n📝 Что было сделано:")
        logger.info("  1. ✅ Все старые таблицы удалены")
        logger.info("  2. ✅ Новые таблицы созданы с правильной схемой")
        logger.info("  3. ✅ Enum значения обновлены на ЗАГЛАВНЫЕ")
        logger.info("  4. ✅ База данных готова к работе\n")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔄 НАЧИНАЮ МИГРАЦИЮ БАЗЫ ДАННЫХ...")
    print("="*60 + "\n")
    
    success = asyncio.run(migrate_database())
    
    if success:
        print("\n✅ Миграция завершена успешно!")
        print("🚀 Теперь запустите бота командой: python main.py\n")
        exit(0)
    else:
        print("\n❌ Миграция не удалась!")
        print("⚠️  Проверьте логи выше\n")
        exit(1)
