# -*- coding: utf-8 -*-
"""
TrixActivity - Database Models для сохранения данных
Интеграция с SQLAlchemy и PostgreSQL
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()

# ============= DATABASE MODELS =============

class TrixUser(Base):
    """Пользователь TrixActivity"""
    __tablename__ = 'trix_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False)
    instagram = Column(String(255))
    threads = Column(String(255))
    
    # Баланс
    balance = Column(Integer, default=0)
    max_balance = Column(Integer, default=15)
    frozen_trixiki = Column(Integer, default=0)
    
    # Статус
    enabled = Column(Boolean, default=True)
    
    # Функции
    active_like = Column(Boolean, default=True)
    active_comment = Column(Boolean, default=True)
    active_follow = Column(Boolean, default=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    last_daily_claim = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrixUser {self.user_id} ({self.username})>"

class TrixTask(Base):
    """Задание в пуле"""
    __tablename__ = 'trix_tasks'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, unique=True, nullable=False, index=True)
    creator_id = Column(Integer, nullable=False, index=True)
    
    # Тип и содержание
    task_type = Column(String(50), nullable=False)  # like, comment, follow
    content = Column(Text, nullable=False)
    cost = Column(Integer, nullable=False)
    
    # Статус
    status = Column(String(50), default='active', index=True)  # active, completed, disputed
    performer_id = Column(Integer, index=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    performed_at = Column(DateTime)
    confirmation_deadline = Column(DateTime)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<TrixTask {self.task_id} ({self.task_type})>"

class TrixConfirmation(Base):
    """Подтверждение задания"""
    __tablename__ = 'trix_confirmations'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False, index=True)
    creator_id = Column(Integer, nullable=False, index=True)
    performer_id = Column(Integer, nullable=False, index=True)
    
    # Статус
    status = Column(String(50), default='pending')  # pending, approved, rejected, auto_confirmed
    amount = Column(Integer, nullable=False)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=False)
    confirmed_at = Column(DateTime)
    confirmed_by = Column(String(50))  # creator, auto, admin
    
    def __repr__(self):
        return f"<TrixConfirmation task_{self.task_id}>"

class TrixStats(Base):
    """Статистика пользователя"""
    __tablename__ = 'trix_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Счетчики
    tasks_created = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_disputed = Column(Integer, default=0)
    
    # Заработанные триксики
    trixiki_earned = Column(Integer, default=0)
    trixiki_spent = Column(Integer, default=0)
    
    # Дневные награды
    daily_claims = Column(Integer, default=0)
    
    # Рейтинг
    reputation = Column(Float, default=0.0)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrixStats user_{self.user_id}>"

class TrixSubscription(Base):
    """Запросы проверки подписок"""
    __tablename__ = 'trix_subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Статус
    status = Column(String(50), default='pending')  # pending, approved, rejected
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    approved_by = Column(Integer)
    
    def __repr__(self):
        return f"<TrixSubscription user_{self.user_id}>"

# ============= DATABASE SERVICE =============

class TrixActivityDatabase:
    """Сервис для работы с БД TrixActivity"""
    
    def __init__(self, session_maker):
        self.session_maker = session_maker
    
    # ============= USER OPERATIONS =============
    
    async def create_user(self, user_id: int, username: str):
        """Создать пользователя в БД"""
        async with self.session_maker() as session:
            user = TrixUser(user_id=user_id, username=username)
            session.add(user)
            await session.commit()
            return user
    
    async def get_user(self, user_id: int):
        """Получить пользователя"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TrixUser).where(TrixUser.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def update_user_balance(self, user_id: int, amount: int):
        """Обновить баланс"""
        async with self.session_maker() as session:
            from sqlalchemy import select, update
            
            user = await session.execute(
                select(TrixUser).where(TrixUser.user_id == user_id)
            )
            user = user.scalar_one_or_none()
            
            if user:
                user.balance = max(0, min(user.balance + amount, user.max_balance))
                user.updated_at = datetime.utcnow()
                await session.commit()
    
    async def update_user_socials(self, user_id: int, instagram: str, threads: str):
        """Обновить социальные аккаунты"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            user = await session.execute(
                select(TrixUser).where(TrixUser.user_id == user_id)
            )
            user = user.scalar_one_or_none()
            
            if user:
                user.instagram = instagram
                user.threads = threads
                user.updated_at = datetime.utcnow()
                await session.commit()
    
    async def set_last_daily_claim(self, user_id: int):
        """Установить время последней дневной награды"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            user = await session.execute(
                select(TrixUser).where(TrixUser.user_id == user_id)
            )
            user = user.scalar_one_or_none()
            
            if user:
                user.last_daily_claim = datetime.utcnow()
                await session.commit()
    
    # ============= TASK OPERATIONS =============
    
    async def create_task(self, task_id: int, creator_id: int, task_type: str, 
                         content: str, cost: int):
        """Создать задание"""
        async with self.session_maker() as session:
            task = TrixTask(
                task_id=task_id,
                creator_id=creator_id,
                task_type=task_type,
                content=content,
                cost=cost
            )
            session.add(task)
            await session.commit()
            return task
    
    async def get_task(self, task_id: int):
        """Получить задание"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TrixTask).where(TrixTask.task_id == task_id)
            )
            return result.scalar_one_or_none()
    
    async def update_task_status(self, task_id: int, status: str, performer_id: int = None):
        """Обновить статус задания"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            task = await session.execute(
                select(TrixTask).where(TrixTask.task_id == task_id)
            )
            task = task.scalar_one_or_none()
            
            if task:
                task.status = status
                if performer_id:
                    task.performer_id = performer_id
                if status == 'completed':
                    task.completed_at = datetime.utcnow()
                await session.commit()
    
    async def get_active_tasks(self, limit: int = 50):
        """Получить активные задания"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TrixTask).where(
                    TrixTask.status == 'active'
                ).limit(limit)
            )
            return result.scalars().all()
    
    # ============= CONFIRMATION OPERATIONS =============
    
    async def create_confirmation(self, task_id: int, creator_id: int, 
                                 performer_id: int, amount: int, deadline):
        """Создать подтверждение"""
        async with self.session_maker() as session:
            conf = TrixConfirmation(
                task_id=task_id,
                creator_id=creator_id,
                performer_id=performer_id,
                amount=amount,
                deadline=deadline
            )
            session.add(conf)
            await session.commit()
            return conf
    
    async def get_pending_confirmations(self, creator_id: int):
        """Получить ожидающие подтверждения"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TrixConfirmation).where(
                    TrixConfirmation.creator_id == creator_id,
                    TrixConfirmation.status == 'pending'
                )
            )
            return result.scalars().all()
    
    async def confirm_task(self, task_id: int, status: str, confirmed_by: str):
        """Подтвердить задание"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            conf = await session.execute(
                select(TrixConfirmation).where(TrixConfirmation.task_id == task_id)
            )
            conf = conf.scalar_one_or_none()
            
            if conf:
                conf.status = status
                conf.confirmed_at = datetime.utcnow()
                conf.confirmed_by = confirmed_by
                await session.commit()
    
    # ============= STATS OPERATIONS =============
    
    async def get_top_users(self, limit: int = 10):
        """Получить топ пользователей"""
        async with self.session_maker() as session:
            from sqlalchemy import select, desc
            result = await session.execute(
                select(TrixUser).order_by(
                    desc(TrixUser.balance)
                ).limit(limit)
            )
            return result.scalars().all()
    
    async def get_user_stats(self, user_id: int):
        """Получить статистику пользователя"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TrixStats).where(TrixStats.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def increment_stat(self, user_id: int, stat_name: str, amount: int = 1):
        """Увеличить статистику"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            stats = await session.execute(
                select(TrixStats).where(TrixStats.user_id == user_id)
            )
            stats = stats.scalar_one_or_none()
            
            if not stats:
                stats = TrixStats(user_id=user_id)
                session.add(stats)
            
            # Увеличиваем нужную статистику
            if hasattr(stats, stat_name):
                setattr(stats, stat_name, getattr(stats, stat_name, 0) + amount)
            
            await session.commit()
    
    # ============= SUBSCRIPTION OPERATIONS =============
    
    async def create_subscription_request(self, user_id: int):
        """Создать запрос проверки подписок"""
        async with self.session_maker() as session:
            sub = TrixSubscription(user_id=user_id)
            session.add(sub)
            await session.commit()
            return sub
    
    async def get_pending_subscriptions(self, limit: int = 50):
        """Получить ожидающие подписки"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TrixSubscription).where(
                    TrixSubscription.status == 'pending'
                ).limit(limit)
            )
            return result.scalars().all()
    
    async def approve_subscription(self, user_id: int, admin_id: int):
        """Одобрить подписку"""
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            sub = await session.execute(
                select(TrixSubscription).where(TrixSubscription.user_id == user_id)
            )
            sub = sub.scalar_one_or_none()
            
            if sub:
                sub.status = 'approved'
                sub.approved_at = datetime.utcnow()
                sub.approved_by = admin_id
                await session.commit()
                
                # Обновляем макс баланс
                user = await session.execute(
                    select(TrixUser).where(TrixUser.user_id == user_id)
                )
                user = user.scalar_one_or_none()
                
                if user:
                    user.max_balance = 20
                    await session.commit()

# Экспорт
__all__ = [
    'Base',
    'TrixUser',
    'TrixTask',
    'TrixConfirmation',
    'TrixStats',
    'TrixSubscription',
    'TrixActivityDatabase'
]
