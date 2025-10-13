# -*- coding: utf-8 -*-
"""
TrixActivity System - Instagram/Threads активность обмен
Система с внутренней валютой "триксики"
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
import asyncio
import logging

logger = logging.getLogger(__name__)

# ============= МОДЕЛИ ДАННЫХ =============

class TrixikiAccount:
    """Аккаунт пользователя с триксиками"""
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.instagram = None
        self.threads = None
        self.balance = 0
        self.max_balance = 15  # Базовый лимит
        self.last_daily_claim = None
        self.frozen_trixiki = 0  # Замороженные триксики
        self.active_functions = {
            'like': True,
            'comment': True,
            'follow': True
        }
        self.enabled = True

class Task:
    """Задание в пуле"""
    def __init__(self, task_id: int, creator_id: int, task_type: str, 
                 content: str, cost: int):
        self.task_id = task_id
        self.creator_id = creator_id
        self.task_type = task_type  # like, comment, follow
        self.content = content
        self.cost = cost
        self.created_at = datetime.now()
        self.status = 'active'  # active, completed, cancelled
        self.performer_id = None
        self.performed_at = None
        self.confirmation_deadline = None

class TrixActivityService:
    """Главный сервис системы триксиков"""
    
    def __init__(self):
        self.accounts: Dict[int, TrixikiAccount] = {}
        self.tasks: Dict[int, Task] = {}
        self.pending_confirmations: Dict[int, Dict] = {}
        self.task_counter = 1
        self.freeze_duration = 3 * 3600  # 3 часа в секундах
        self.daily_reward = 10
        self.daily_reset_hour = 0
        
        # Цены действий
        self.prices = {
            'like': 3,
            'comment': 4,
            'follow': 5
        }
        
        # Лимиты действий
        self.limits = {
            'like': 5,  # максимум 5 постов
            'comment': 2,  # максимум 2 поста
            'follow': 1  # 1 аккаунт
        }
    
    # ============= РЕГИСТРАЦИЯ =============
    
    def register_user(self, user_id: int, username: str) -> TrixikiAccount:
        """Регистрация нового пользователя"""
        if user_id in self.accounts:
            return self.accounts[user_id]
        
        account = TrixikiAccount(user_id, username)
        self.accounts[user_id] = account
        logger.info(f"User {user_id} registered in TrixActivity")
        return account
    
    def set_social_accounts(self, user_id: int, instagram: str, threads: str) -> bool:
        """Установить социальные аккаунты"""
        if user_id not in self.accounts:
            return False
        
        account = self.accounts[user_id]
        account.instagram = instagram.lstrip('@')
        account.threads = threads.lstrip('@')
        logger.info(f"User {user_id} set socials: IG={instagram}, Threads={threads}")
        return True
    
    # ============= БАЛАНС И ТРИКСИКИ =============
    
    async def claim_daily_reward(self, user_id: int) -> tuple[bool, int, str]:
        """Получить дневную награду"""
        if user_id not in self.accounts:
            return False, 0, "❌ Аккаунт не найден"
        
        account = self.accounts[user_id]
        
        # Проверяем, получал ли уже сегодня
        now = datetime.now()
        if account.last_daily_claim:
            last_claim = account.last_daily_claim
            if (last_claim.date() == now.date()):
                return False, account.balance, "⏰ Вы уже получили награду сегодня"
        
        # Проверяем максимальный баланс
        if account.balance >= account.max_balance:
            return False, account.balance, (
                f"📊 Ваш баланс ({account.balance}) на максимуме ({account.max_balance})"
            )
        
        # Добавляем награду
        reward = min(self.daily_reward, account.max_balance - account.balance)
        account.balance += reward
        account.last_daily_claim = now
        
        return True, account.balance, (
            f"✅ Получено {reward} триксиков!\n"
            f"💰 Баланс: {account.balance}/{account.max_balance}"
        )
    
    def get_balance(self, user_id: int) -> tuple[int, int, int]:
        """Получить баланс (текущий, макс, замороженный)"""
        if user_id not in self.accounts:
            return 0, 15, 0
        
        account = self.accounts[user_id]
        return account.balance, account.max_balance, account.frozen_trixiki
    
    def can_afford_action(self, user_id: int, action: str) -> tuple[bool, str]:
        """Проверить, может ли пользователь оплатить действие"""
        if user_id not in self.accounts:
            return False, "❌ Аккаунт не найден"
        
        account = self.accounts[user_id]
        
        if not account.enabled:
            return False, "❌ Ваш аккаунт отключен администратором"
        
        if not account.active_functions.get(action, False):
            return False, f"❌ Функция '{action}' отключена"
        
        cost = self.prices.get(action, 0)
        available = account.balance - account.frozen_trixiki
        
        if available < cost:
            return False, (
                f"❌ Недостаточно триксиков!\n"
                f"💰 Доступно: {available}\n"
                f"💸 Нужно: {cost}"
            )
        
        return True, "✅"
    
    # ============= СОЗДАНИЕ ЗАДАНИЙ =============
    
    def create_task(self, user_id: int, task_type: str, links: List[str]) -> tuple[bool, int, str]:
        """Создать новое задание"""
        if user_id not in self.accounts:
            return False, 0, "❌ Аккаунт не найден"
        
        account = self.accounts[user_id]
        
        # Проверяем возможность оплатить
        can_afford, msg = self.can_afford_action(user_id, task_type)
        if not can_afford:
            return False, 0, msg
        
        # Проверяем количество ссылок
        max_links = self.limits.get(task_type, 1)
        if len(links) > max_links:
            return False, 0, (
                f"❌ Максимум {max_links} ссылок для {task_type}\n"
                f"Вы указали: {len(links)}"
            )
        
        # Создаем задание
        cost = self.prices[task_type]
        content = "|".join(links)
        
        task = Task(
            self.task_counter,
            user_id,
            task_type,
            content,
            cost
        )
        
        self.tasks[self.task_counter] = task
        task_id = self.task_counter
        self.task_counter += 1
        
        # Списываем триксики
        account.balance -= cost
        logger.info(f"Task {task_id} created by user {user_id} (type: {task_type})")
        
        return True, task_id, (
            f"✅ Задание создано!\n"
            f"🆔 ID: {task_id}\n"
            f"💸 Стоимость: {cost} триксиков\n"
            f"💰 Баланс: {account.balance}/{account.max_balance}"
        )
    
    # ============= ПУЛ ЗАДАНИЙ =============
    
    def get_active_tasks(self, user_id: int) -> List[Task]:
        """Получить активные задания (кроме своих)"""
        user_tasks = []
        
        for task in self.tasks.values():
            # Пропускаем свои задания
            if task.creator_id == user_id:
                continue
            
            # Только активные
            if task.status != 'active':
                continue
            
            # Проверяем, есть ли у пользователя нужная функция
            creator = self.accounts.get(task.creator_id)
            if not creator or not creator.active_functions.get(task.task_type):
                continue
            
            user_tasks.append(task)
        
        return user_tasks
    
    # ============= ВЫПОЛНЕНИЕ ЗАДАНИЙ =============
    
    def perform_task(self, task_id: int, performer_id: int) -> tuple[bool, str]:
        """Пользователь отмечает задание как выполненное"""
        if task_id not in self.tasks:
            return False, "❌ Задание не найдено"
        
        if performer_id not in self.accounts:
            return False, "❌ Аккаунт не найден"
        
        task = self.tasks[task_id]
        account = self.accounts[performer_id]
        
        if task.status != 'active':
            return False, "❌ Задание не активно"
        
        if task.performer_id is not None:
            return False, "❌ Задание уже выполняется"
        
        # Замораживаем триксики исполнителю
        account.frozen_trixiki += task.cost
        
        # Отмечаем задание
        task.performer_id = performer_id
        task.performed_at = datetime.now()
        task.confirmation_deadline = datetime.now() + timedelta(seconds=self.freeze_duration)
        
        # Добавляем в ожидающие подтверждения
        self.pending_confirmations[task_id] = {
            'creator_id': task.creator_id,
            'performer_id': performer_id,
            'task_id': task_id,
            'created_at': datetime.now(),
            'deadline': task.confirmation_deadline,
            'cost': task.cost
        }
        
        logger.info(f"Task {task_id} performed by user {performer_id}")
        
        return True, (
            f"✅ Задание отмечено как выполненное!\n"
            f"🆔 Task ID: {task_id}\n"
            f"⏳ Создатель должен подтвердить в течение 3 часов\n"
            f"💰 После подтверждения вы получите {task.cost} триксиков"
        )
    
    def confirm_task(self, task_id: int, user_id: int, approve: bool) -> tuple[bool, str]:
        """Создатель подтверждает или отклоняет выполнение"""
        if task_id not in self.tasks:
            return False, "❌ Задание не найдено"
        
        task = self.tasks[task_id]
        
        if task.creator_id != user_id:
            return False, "❌ Вы не создатель этого задания"
        
        if task.performer_id is None:
            return False, "❌ Задание еще не выполняется"
        
        performer = self.accounts.get(task.performer_id)
        creator = self.accounts.get(task.creator_id)
        
        if not performer or not creator:
            return False, "❌ Аккаунт не найден"
        
        # Разморозить триксики исполнителю
        performer.frozen_trixiki -= task.cost
        
        if approve:
            # Переводим триксики
            performer.balance += task.cost
            task.status = 'completed'
            
            msg = (
                f"✅ Задание #{task_id} подтверждено!\n"
                f"💰 Исполнитель @{performer.username} получил {task.cost} триксиков"
            )
        else:
            # Отклоняем - будет отправлено админам
            task.status = 'disputed'
            
            msg = (
                f"❌ Задание #{task_id} отклонено!\n"
                f"📋 Информация отправлена администраторам"
            )
        
        # Удаляем из ожидающих
        if task_id in self.pending_confirmations:
            del self.pending_confirmations[task_id]
        
        logger.info(f"Task {task_id} {'approved' if approve else 'rejected'} by creator {user_id}")
        
        return True, msg
    
    async def auto_confirm_expired_tasks(self) -> List[int]:
        """Автоматическое подтверждение истекших заданий"""
        confirmed = []
        now = datetime.now()
        
        for task_id, confirmation in list(self.pending_confirmations.items()):
            if confirmation['deadline'] < now:
                task = self.tasks.get(task_id)
                if task and task.status == 'active' and task.performer_id:
                    
                    performer = self.accounts.get(task.performer_id)
                    if performer:
                        # Автоподтверждение
                        performer.frozen_trixiki -= task.cost
                        performer.balance += task.cost
                        task.status = 'completed'
                        confirmed.append(task_id)
                    
                    del self.pending_confirmations[task_id]
        
        if confirmed:
            logger.info(f"Auto-confirmed {len(confirmed)} tasks: {confirmed}")
        
        return confirmed
    
    # ============= ПРОВЕРКА ПОДПИСОК =============
    
    def request_subscription_check(self, user_id: int) -> tuple[bool, str]:
        """Запросить проверку подписок для увеличения лимита"""
        if user_id not in self.accounts:
            return False, "❌ Аккаунт не найден"
        
        account = self.accounts[user_id]
        
        if account.max_balance >= 20:
            return True, "✅ Ваш лимит уже максимален (20 триксиков)"
        
        # Добавляем в ожидающие проверки (для админов)
        # В реальной системе это будет отправлено в админ-группу
        
        return True, (
            f"📋 Запрос на проверку подписок отправлен!\n"
            f"✅ Убедитесь, что подписаны на:\n"
            f"  • Instagram @budapesttrix\n"
            f"  • Threads @budapesttrix\n\n"
            f"⏳ Администратор проверит в течение 24 часов"
        )
    
    # ============= АДМИН ФУНКЦИИ =============
    
    def admin_enable_user(self, user_id: int) -> tuple[bool, str]:
        """Включить пользователя"""
        if user_id not in self.accounts:
            return False, "❌ Пользователь не найден"
        
        self.accounts[user_id].enabled = True
        return True, f"✅ Пользователь {user_id} включен"
    
    def admin_disable_user(self, user_id: int) -> tuple[bool, str]:
        """Отключить пользователя"""
        if user_id not in self.accounts:
            return False, "❌ Пользователь не найден"
        
        self.accounts[user_id].enabled = False
        return True, f"✅ Пользователь {user_id} отключен"
    
    def admin_add_trixiki(self, user_id: int, amount: int) -> tuple[bool, str]:
        """Добавить триксики пользователю"""
        if user_id not in self.accounts:
            return False, "❌ Пользователь не найден"
        
        account = self.accounts[user_id]
        old_balance = account.balance
        account.balance = min(account.balance + amount, account.max_balance)
        added = account.balance - old_balance
        
        return True, (
            f"✅ Добавлено {added} триксиков пользователю {user_id}\n"
            f"💰 Новый баланс: {account.balance}/{account.max_balance}"
        )
    
    def admin_increase_limit(self, user_id: int) -> tuple[bool, str]:
        """Увеличить лимит пользователя до 20"""
        if user_id not in self.accounts:
            return False, "❌ Пользователь не найден"
        
        account = self.accounts[user_id]
        
        if account.max_balance >= 20:
            return False, "❌ Лимит уже на максимуме"
        
        account.max_balance = 20
        return True, (
            f"✅ Лимит увеличен для пользователя {user_id}\n"
            f"📊 Новый максимум: 20 триксиков"
        )
    
    def admin_dispute_report(self, task_id: int) -> str:
        """Получить отчет о споре"""
        if task_id not in self.tasks:
            return "❌ Задание не найдено"
        
        task = self.tasks[task_id]
        creator = self.accounts.get(task.creator_id)
        performer = self.accounts.get(task.performer_id)
        
        report = (
            f"📋 ОТЧЕТ ПО СПОРУ #{task_id}\n\n"
            f"👤 Создатель: @{creator.username if creator else 'unknown'} (ID: {task.creator_id})\n"
            f"👤 Исполнитель: @{performer.username if performer else 'unknown'} (ID: {task.performer_id})\n"
            f"📌 Тип: {task.task_type.upper()}\n"
            f"💰 Сумма: {task.cost} триксиков\n"
            f"📅 Создано: {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📅 Выполнено: {task.performed_at.strftime('%d.%m.%Y %H:%M') if task.performed_at else 'N/A'}\n\n"
            f"📝 Содержание: {task.content[:100]}...\n"
        )
        
        return report
    
    # ============= СТАТИСТИКА =============
    
    def get_top_users(self, limit: int = 10) -> List[tuple]:
        """Получить топ пользователей по триксикам"""
        sorted_users = sorted(
            self.accounts.values(),
            key=lambda a: a.balance,
            reverse=True
        )
        
        return [(u.username, u.balance, u.max_balance) for u in sorted_users[:limit]]
    
    def get_task_stats(self) -> Dict:
        """Получить статистику заданий"""
        active = sum(1 for t in self.tasks.values() if t.status == 'active')
        completed = sum(1 for t in self.tasks.values() if t.status == 'completed')
        disputed = sum(1 for t in self.tasks.values() if t.status == 'disputed')
        
        by_type = {}
        for task in self.tasks.values():
            by_type.setdefault(task.task_type, 0)
            by_type[task.task_type] += 1
        
        return {
            'active': active,
            'completed': completed,
            'disputed': disputed,
            'total': len(self.tasks),
            'by_type': by_type,
            'pending_confirmations': len(self.pending_confirmations)
        }

# Глобальный экземпляр
trix_activity = TrixActivityService()
