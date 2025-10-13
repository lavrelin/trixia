# -*- coding: utf-8 -*-
"""
TrixActivity - Unit Tests & Integration Tests
Тестирование всех компонентов системы
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from handlers.trix_activity_service import (
    TrixActivityService, TrixikiAccount, Task
)

# ============= FIXTURES =============

@pytest.fixture
def service():
    """Создать сервис для тестирования"""
    return TrixActivityService()

@pytest.fixture
def user_id():
    return 12345

@pytest.fixture
def username():
    return "testuser"

# ============= TESTS: РЕГИСТРАЦИЯ =============

class TestRegistration:
    """Тесты регистрации пользователей"""
    
    def test_register_new_user(self, service, user_id, username):
        """Регистрация нового пользователя"""
        account = service.register_user(user_id, username)
        
        assert account is not None
        assert account.user_id == user_id
        assert account.username == username
        assert account.balance == 0
        assert account.max_balance == 15
    
    def test_register_existing_user(self, service, user_id, username):
        """Повторная регистрация возвращает существующий аккаунт"""
        account1 = service.register_user(user_id, username)
        account2 = service.register_user(user_id, username)
        
        assert account1 is account2
    
    def test_set_socials(self, service, user_id, username):
        """Установка социальных аккаунтов"""
        service.register_user(user_id, username)
        
        success = service.set_social_accounts(user_id, "@ig_account", "@threads_account")
        
        assert success is True
        assert service.accounts[user_id].instagram == "ig_account"
        assert service.accounts[user_id].threads == "threads_account"

# ============= TESTS: БАЛАНС И НАГРАДЫ =============

class TestBalance:
    """Тесты работы с балансом"""
    
    @pytest.mark.asyncio
    async def test_claim_daily_reward(self, service, user_id, username):
        """Получение дневной награды"""
        service.register_user(user_id, username)
        
        success, balance, msg = await service.claim_daily_reward(user_id)
        
        assert success is True
        assert balance == 10  # ежедневный награда
        assert "Получено 10 триксиков" in msg
    
    @pytest.mark.asyncio
    async def test_cannot_claim_twice(self, service, user_id, username):
        """Нельзя получить награду дважды в день"""
        service.register_user(user_id, username)
        
        # Первый клейм
        await service.claim_daily_reward(user_id)
        
        # Второй клейм должен не пройти
        success, balance, msg = await service.claim_daily_reward(user_id)
        
        assert success is False
        assert "уже получили награду" in msg
    
    @pytest.mark.asyncio
    async def test_max_balance_cap(self, service, user_id, username):
        """Баланс не может превысить максимум"""
        service.register_user(user_id, username)
        account = service.accounts[user_id]
        account.balance = 14
        
        success, balance, msg = await service.claim_daily_reward(user_id)
        
        assert success is True
        assert balance == 15  # максимум
    
    def test_get_balance(self, service, user_id, username):
        """Получение информации о балансе"""
        service.register_user(user_id, username)
        
        current, max_bal, frozen = service.get_balance(user_id)
        
        assert current == 0
        assert max_bal == 15
        assert frozen == 0

# ============= TESTS: СОЗДАНИЕ ЗАДАНИЙ =============

class TestTaskCreation:
    """Тесты создания заданий"""
    
    def test_create_task_success(self, service, user_id, username):
        """Успешное создание задания"""
        service.register_user(user_id, username)
        account = service.accounts[user_id]
        account.balance = 5  # Достаточно триксиков
        
        success, task_id, msg = service.create_task(
            user_id, 'like', 
            ['https://instagram.com/p/ABC123']
        )
        
        assert success is True
        assert task_id > 0
        assert account.balance == 2  # 5 - 3 за like
    
    def test_insufficient_balance(self, service, user_id, username):
        """Ошибка при недостаточном балансе"""
        service.register_user(user_id, username)
        account = service.accounts[user_id]
        account.balance = 1  # Слишком мало
        
        success, task_id, msg = service.create_task(
            user_id, 'like',
            ['https://instagram.com/p/ABC123']
        )
        
        assert success is False
        assert "Недостаточно триксиков" in msg
    
    def test_too_many_links(self, service, user_id, username):
        """Ошибка при слишком многих ссылках"""
        service.register_user(user_id, username)
        account = service.accounts[user_id]
        account.balance = 10
        
        success, task_id, msg = service.create_task(
            user_id, 'like',
            ['link1', 'link2', 'link3', 'link4', 'link5', 'link6']  # 6 > макс 5
        )
        
        assert success is False
        assert "Максимум" in msg

# ============= TESTS: ПУЛ ЗАДАНИЙ =============

class TestTaskPool:
    """Тесты пула заданий"""
    
    def test_get_active_tasks(self, service):
        """Получить активные задания"""
        # Создаем несколько пользователей
        user1 = service.register_user(1, "user1")
        user1.balance = 10
        user2 = service.register_user(2, "user2")
        
        # Создаем задания
        service.create_task(1, 'like', ['link1'])
        service.create_task(1, 'comment', ['link2'])
        
        # Получаем задания для user2
        tasks = service.get_active_tasks(2)
        
        assert len(tasks) >= 2
        assert all(t.creator_id == 1 for t in tasks)
        assert all(t.creator_id != 2 for t in tasks)  # Не свои задания
    
    def test_own_tasks_excluded(self, service):
        """Свои задания не показываются в пуле"""
        user1 = service.register_user(1, "user1")
        user1.balance = 10
        
        service.create_task(1, 'like', ['link1'])
        
        # Смотрим пул для того же пользователя
        tasks = service.get_active_tasks(1)
        
        assert len(tasks) == 0  # Нет чужих заданий

# ============= TESTS: ВЫПОЛНЕНИЕ ЗАДАНИЙ =============

class TestTaskExecution:
    """Тесты выполнения заданий"""
    
    def test_perform_task(self, service):
        """Выполнение задания"""
        # Setup
        creator = service.register_user(1, "creator")
        creator.balance = 10
        performer = service.register_user(2, "performer")
        
        # Создаем задание
        _, task_id, _ = service.create_task(1, 'like', ['link1'])
        
        # Выполняем
        success, msg = service.perform_task(task_id, 2)
        
        assert success is True
        assert performer.frozen_trixiki == 3
        assert service.tasks[task_id].performer_id == 2
    
    def test_confirm_task_approve(self, service):
        """Подтверждение (одобрение) задания"""
        # Setup
        creator = service.register_user(1, "creator")
        creator.balance = 10
        performer = service.register_user(2, "performer")
        
        # Создаем и выполняем
        _, task_id, _ = service.create_task(1, 'like', ['link1'])
        service.perform_task(task_id, 2)
        
        # Подтверждаем
        success, msg = service.confirm_task(task_id, 1, approve=True)
        
        assert success is True
        assert performer.balance == 3
        assert performer.frozen_trixiki == 0
    
    def test_confirm_task_reject(self, service):
        """Отклонение задания"""
        # Setup
        creator = service.register_user(1, "creator")
        creator.balance = 10
        performer = service.register_user(2, "performer")
        
        # Создаем и выполняем
        _, task_id, _ = service.create_task(1, 'like', ['link1'])
        service.perform_task(task_id, 2)
        
        # Отклоняем
        success, msg = service.confirm_task(task_id, 1, approve=False)
        
        assert success is True
        assert performer.balance == 0  # Не получил триксики
        assert performer.frozen_trixiki == 0

# ============= TESTS: АДМИН ФУНКЦИИ =============

class TestAdminFunctions:
    """Тесты админских функций"""
    
    def test_enable_user(self, service, user_id, username):
        """Включить пользователя"""
        service.register_user(user_id, username)
        service.accounts[user_id].enabled = False
        
        success, msg = service.admin_enable_user(user_id)
        
        assert success is True
        assert service.accounts[user_id].enabled is True
    
    def test_disable_user(self, service, user_id, username):
        """Отключить пользователя"""
        service.register_user(user_id, username)
        
        success, msg = service.admin_disable_user(user_id)
        
        assert success is True
        assert service.accounts[user_id].enabled is False
    
    def test_add_trixiki(self, service, user_id, username):
        """Добавить триксики"""
        service.register_user(user_id, username)
        
        success, msg = service.admin_add_trixiki(user_id, 5)
        
        assert success is True
        assert service.accounts[user_id].balance == 5

# ============= TESTS: СТАТИСТИКА =============

class TestStatistics:
    """Тесты статистики"""
    
    def test_get_top_users(self, service):
        """Получить топ пользователей"""
        # Создаем пользователей с разными балансами
        user1 = service.register_user(1, "user1")
        user1.balance = 20
        
        user2 = service.register_user(2, "user2")
        user2.balance = 15
        
        user3 = service.register_user(3, "user3")
        user3.balance = 10
        
        top = service.get_top_users(2)
        
        assert len(top) == 2
        assert top[0][1] == 20  # Первый имеет 20
        assert top[1][1] == 15  # Второй имеет 15
    
    def test_get_task_stats(self, service):
        """Получить статистику заданий"""
        creator = service.register_user(1, "creator")
        creator.balance = 20
        
        # Создаем задания
        service.create_task(1, 'like', ['link1'])
        service.create_task(1, 'comment', ['link2'])
        service.create_task(1, 'follow', ['link3'])
        
        stats = service.get_task_stats()
        
        assert stats['active'] == 3
        assert stats['total'] == 3
        assert stats['by_type']['like'] == 1
        assert stats['by_type']['comment'] == 1
        assert stats['by_type']['follow'] == 1

# ============= INTEGRATION TESTS =============

class TestIntegration:
    """Интеграционные тесты полного цикла"""
    
    @pytest.mark.asyncio
    async def test_full_cycle(self, service):
        """Полный цикл: создание, выполнение, подтверждение"""
        # Setup
        creator = service.register_user(1, "creator")
        creator.balance = 15
        
        performer = service.register_user(2, "performer")
        
        # Шаг 1: Создание
        success, task_id, _ = service.create_task(1, 'like', ['link'])
        assert success is True
        assert creator.balance == 12
        
        # Шаг 2: Получение награды
        success, _, _ = await service.claim_daily_reward(2)
        assert success is True
        assert performer.balance == 10
        
        # Шаг 3: Выполнение
        success, _ = service.perform_task(task_id, 2)
        assert success is True
        assert performer.frozen_trixiki == 3
        
        # Шаг 4: Подтверждение
        success, _ = service.confirm_task(task_id, 1, approve=True)
        assert success is True
        assert performer.balance == 13  # 10 + 3
        assert performer.frozen_trixiki == 0

# ============= RUN TESTS =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
