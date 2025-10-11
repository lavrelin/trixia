# -*- coding: utf-8 -*-
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from config import Config
from contextlib import asynccontextmanager
import logging
import re

logger = logging.getLogger(__name__)

Base = declarative_base()

class Publication(Base):
    """Модель публикации"""
    __tablename__ = 'publications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(255))
    text = Column(Text)
    media_type = Column(String(50))
    media_file_id = Column(String(255))
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    moderated_at = Column(DateTime)
    moderator_id = Column(Integer)

class PiarRequest(Base):
    """Модель заявки на пиар"""
    __tablename__ = 'piar_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(255))
    category = Column(String(100))
    subcategory = Column(String(100))
    district = Column(String(100))
    title = Column(String(255))
    description = Column(Text)
    phone = Column(String(50))
    link = Column(String(500))
    media_file_ids = Column(Text)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    moderated_at = Column(DateTime)
    moderator_id = Column(Integer)

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.engine = None
        self.session_maker = None
    
    async def init(self):
        """Инициализация базы данных"""
        try:
            db_url = Config.DATABASE_URL
            
            logger.info("🔍 DATABASE INITIALIZATION")
            logger.info(f"Raw DATABASE_URL: {db_url[:60]}...")
            
            # ИСПРАВЛЕНИЕ: Правильная конвертация URL для async
            if not db_url:
                logger.error("❌ DATABASE_URL is empty!")
                raise ValueError("DATABASE_URL not configured")
            
            # Конвертируем postgresql:// в postgresql+asyncpg://
            if db_url.startswith('postgresql://'):
                db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
                logger.info("✅ Converted postgresql:// → postgresql+asyncpg://")
            
            elif db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql+asyncpg://', 1)
                logger.info("✅ Converted postgres:// → postgresql+asyncpg://")
            
            elif db_url.startswith('sqlite:///'):
                db_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)
                logger.info("✅ Converted sqlite:// → sqlite+aiosqlite://")
            
            elif db_url.startswith('sqlite://'):
                db_url = db_url.replace('sqlite://', 'sqlite+aiosqlite:///', 1)
                logger.info("✅ Converted sqlite:// → sqlite+aiosqlite://")
            
            logger.info(f"✅ Final DATABASE_URL: {db_url[:60]}...")
            
            # ИСПРАВЛЕНИЕ: Определяем параметры подключения в зависимости от БД
            connect_args = {}
            pool_size = 5
            max_overflow = 10
            
            if 'postgresql' in db_url:
                logger.info("📊 Database: PostgreSQL with asyncpg")
                connect_args = {
                    'ssl': 'require',
                    'timeout': 30,
                    'command_timeout': 30
                }
                pool_size = 10
                max_overflow = 20
            
            elif 'sqlite' in db_url:
                logger.info("📊 Database: SQLite with aiosqlite")
                connect_args = {
                    'timeout': 30,
                    'check_same_thread': False
                }
                pool_size = 1
                max_overflow = 0
            
            else:
                logger.warning(f"⚠️  Unknown database type in: {db_url[:50]}")
            
            logger.info(f"🔧 Connection args: {connect_args}")
            
            # Создаем engine
            logger.info("⏳ Creating async engine...")
            
            self.engine = create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=pool_size,
                max_overflow=max_overflow,
                connect_args=connect_args if connect_args else None
            )
            
            logger.info("✅ Engine created")
            
            # Создаем session maker
            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("✅ Session maker created")
            
            # Тестируем подключение
            logger.info("⏳ Testing connection...")
            try:
                async with self.engine.connect() as conn:
                    from sqlalchemy import text
                    result = await conn.execute(text("SELECT 1"))
                    value = result.scalar()
                    logger.info(f"✅ Connection test successful (result: {value})")
            except Exception as test_error:
                logger.error(f"❌ Connection test failed: {test_error}")
                logger.error(f"   Type: {type(test_error).__name__}")
                logger.error(f"   Message: {str(test_error)[:200]}")
                raise
            
            # Создаем таблицы
            logger.info("⏳ Creating tables...")
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Tables created")
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}", exc_info=True)
            logger.error("")
            logger.error("🔍 Debugging:")
            logger.error(f"  DATABASE_URL: {Config.DATABASE_URL[:60]}...")
            logger.error(f"  Error type: {type(e).__name__}")
            logger.error("")
            logger.error("💡 Solutions:")
            logger.error("  1. Check if PostgreSQL is running/accessible")
            logger.error("  2. Verify DATABASE_URL format is correct")
            logger.error("  3. On Railway: Delete PostgreSQL service and create it again")
            logger.error("  4. Wait 3-5 minutes after creating PostgreSQL on Railway")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Получить сессию базы данных"""
        if not self.session_maker:
            logger.warning("Database not initialized, attempting init...")
            await self.init()
        
        if not self.session_maker:
            logger.error("Database session unavailable - using dummy session")
            
            class DummySession:
                async def execute(self, *args, **kwargs):
                    logger.warning("Dummy session execute called")
                    return None
                async def commit(self):
                    logger.warning("Dummy session commit called")
                async def rollback(self):
                    logger.warning("Dummy session rollback called")
                async def close(self):
                    pass
                async def flush(self):
                    pass
                async def refresh(self, *args):
                    pass
                def add(self, *args):
                    pass
            
            try:
                yield DummySession()
            finally:
                pass
            return
        
        async with self.session_maker() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Закрыть соединение с базой данных"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

# Глобальный экземпляр базы данных
db = Database()

__all__ = ['db', 'Publication', 'PiarRequest', 'Base']
