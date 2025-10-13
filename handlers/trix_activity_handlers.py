# -*- coding: utf-8 -*-
"""
TrixActivity - Обработчики команд для Telegram бота
Интеграция с главным ботом TrixLiveBot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
import logging
from datetime import datetime

# Импортируем сервис из главного файла
from handlers.trix_activity_service import trix_activity

logger = logging.getLogger(__name__)

# ============= РЕГИСТРАЦИЯ =============

async def liketime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Регистрация в TrixActivity - /liketime"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    # Регистрируем пользователя
    account = trix_activity.register_user(user_id, username)
    
    keyboard = [
        [
            InlineKeyboardButton("📷 Instagram", callback_data="lt:ig"),
            InlineKeyboardButton("🌀 Threads", callback_data="lt:threads")
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="menu:back")]
    ]
    
    text = (
        "👋 **Добро пожаловать в TrixActivity!**\n\n"
        "🎯 Система обмена активностью в Instagram и Threads\n\n"
        
        "💰 **Триксики** - внутренняя валюта:\n"
        "• Ежедневно: +10 триксиков\n"
        "• Максимум: 15 триксиков (20 после проверки подписок)\n\n"
        
        "📊 **Стоимость действий:**\n"
        "• ❤️ Like → 3 триксика (макс 5 постов)\n"
        "• 💬 Comment → 4 триксика (макс 2 поста)\n"
        "• ➕ Follow → 5 триксиков (1 аккаунт)\n\n"
        
        "📝 **Сначала укажите ваши аккаунты:**"
    )
    
    context.user_data['lt_step'] = 'waiting_ig'
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_lt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback'ов регистрации"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    
    user_id = update.effective_user.id
    
    if action == "ig":
        context.user_data['lt_step'] = 'waiting_ig'
        
        keyboard = [[InlineKeyboardButton("⏮️ Назад", callback_data="lt:back")]]
        
        await query.edit_message_text(
            "📷 **Укажите свой Instagram аккаунт:**\n\n"
            "Пример: `@myinstagram` или `myinstagram`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "threads":
        context.user_data['lt_step'] = 'waiting_threads'
        
        keyboard = [[InlineKeyboardButton("⏮️ Назад", callback_data="lt:back")]]
        
        await query.edit_message_text(
            "🌀 **Укажите свой Threads аккаунт:**\n\n"
            "Пример: `@mythreads` или `mythreads`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif action == "back":
        await liketime_command(update, context)

async def handle_lt_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода аккаунтов"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Сначала используйте /liketime")
        return
    
    account = trix_activity.accounts[user_id]
    step = context.user_data.get('lt_step')
    
    if step == 'waiting_ig':
        account.instagram = text.lstrip('@')
        context.user_data['lt_step'] = 'waiting_threads'
        
        keyboard = [[InlineKeyboardButton("⏭️ Далее", callback_data="lt:threads")]]
        
        await update.message.reply_text(
            f"✅ Instagram сохранен: @{account.instagram}\n\n"
            f"🌀 Теперь укажите Threads аккаунт:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif step == 'waiting_threads':
        account.threads = text.lstrip('@')
        context.user_data['lt_step'] = 'completed'
        
        await show_main_menu(update, context)

# ============= ГЛАВНОЕ МЕНЮ =============

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню TrixActivity"""
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Используйте /liketime для регистрации")
        return
    
    account = trix_activity.accounts[user_id]
    balance, max_balance, frozen = trix_activity.get_balance(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("💰 Баланс", callback_data="lt:balance"),
            InlineKeyboardButton("📊 Статистика", callback_data="lt:stats")
        ],
        [
            InlineKeyboardButton("➕ Создать", callback_data="lt:create"),
            InlineKeyboardButton("📋 Пул заданий", callback_data="lt:pool")
        ],
        [
            InlineKeyboardButton("⚙️ Функции", callback_data="lt:settings"),
            InlineKeyboardButton("📱 Подписки", callback_data="lt:subscribe")
        ]
    ]
    
    text = (
        f"🎯 **TrixActivity**\n\n"
        f"👤 Ник: @{account.username}\n"
        f"📷 Instagram: @{account.instagram or '❌ не указан'}\n"
        f"🌀 Threads: @{account.threads or '❌ не указан'}\n\n"
        
        f"💰 **Баланс:** {balance}/{max_balance} триксиков\n"
        f"🔒 **Заморожено:** {frozen} триксиков\n"
        f"📍 **Статус:** {'✅ Активен' if account.enabled else '❌ Отключен'}"
    )
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")

# ============= БАЛАНС И НАГРАДЫ =============

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить дневную награду - /trixiki или кнопка"""
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Используйте /liketime для регистрации")
        return
    
    # Пытаемся получить награду
    success, balance, message = await trix_activity.claim_daily_reward(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="lt:balance")],
        [InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============= СОЗДАНИЕ ЗАДАНИЙ =============

async def create_task_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню создания заданий"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await query.answer("❌ Используйте /liketime", show_alert=True)
        return
    
    account = trix_activity.accounts[user_id]
    balance, max_balance, frozen = trix_activity.get_balance(user_id)
    available = balance - frozen
    
    keyboard = [
        [
            InlineKeyboardButton("❤️ Like (3)", callback_data="lt:create:like"),
            InlineKeyboardButton("💬 Comment (4)", callback_data="lt:create:comment")
        ],
        [InlineKeyboardButton("➕ Follow (5)", callback_data="lt:create:follow")],
        [InlineKeyboardButton("◀️ Назад", callback_data="lt:menu")]
    ]
    
    text = (
        f"📝 **Создать задание**\n\n"
        f"💰 Доступно: {available} триксиков\n\n"
        
        f"**Выберите тип действия:**\n\n"
        f"❤️ **Like** - 3 триксика (макс 5 ссылок)\n"
        f"💬 **Comment** - 4 триксика (макс 2 ссылки)\n"
        f"➕ **Follow** - 5 триксиков (1 аккаунт)\n"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_create_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора действия для создания"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data.split(":")
    action_type = data[2] if len(data) > 2 else None
    
    if not action_type:
        return
    
    context.user_data['lt_create_type'] = action_type
    
    max_links = trix_activity.limits.get(action_type, 1)
    
    if action_type == 'follow':
        prompt = (
            f"➕ **Добавить в Follow**\n\n"
            f"Укажите аккаунт Instagram, который нужно подписать:\n\n"
            f"Пример: `@myaccount` или `https://instagram.com/myaccount`"
        )
    else:
        prompt = (
            f"{'❤️' if action_type == 'like' else '💬'} **Укажите ссылки**\n\n"
            f"Отправьте {max_links} ссылку(ссылки) на пост(ы)\n"
            f"Каждую ссылку - с новой строки\n\n"
            f"Пример:\n"
            f"`https://instagram.com/p/ABC123`\n"
            f"`https://instagram.com/p/DEF456`"
        )
    
    keyboard = [[InlineKeyboardButton("◀️ Отмена", callback_data="lt:create")]]
    
    context.user_data['lt_step'] = f'create_{action_type}'
    
    await query.edit_message_text(
        prompt,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_create_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ссылок для создания задания"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get('lt_step', '')
    
    if not step.startswith('create_'):
        return
    
    action_type = step.replace('create_', '')
    
    # Парсим ссылки
    links = [link.strip() for link in text.split('\n') if link.strip()]
    
    if not links:
        await update.message.reply_text("❌ Укажите хотя бы одну ссылку")
        return
    
    # Создаем задание
    success, task_id, message = trix_activity.create_task(user_id, action_type, links)
    
    if success:
        keyboard = [
            [InlineKeyboardButton("📋 В пул", callback_data="lt:pool")],
            [InlineKeyboardButton("➕ Еще", callback_data="lt:create")],
            [InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]
        ]
    else:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="lt:create")]]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    context.user_data['lt_step'] = None

# ============= ПУЛ ЗАДАНИЙ =============

async def show_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать пул активных заданий"""
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Используйте /liketime")
        return
    
    account = trix_activity.accounts[user_id]
    tasks = trix_activity.get_active_tasks(user_id)
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]]
        
        await update.message.reply_text(
            "📭 **Пул пуст!**\n\n"
            "Сейчас нет активных заданий.\n"
            "Попробуйте позже или создайте собственное!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Показываем первое задание
    task = tasks[0]
    creator = trix_activity.accounts.get(task.creator_id)
    
    text = (
        f"📋 **Пул заданий** ({len(tasks)} активных)\n\n"
        f"🆔 Task ID: {task.task_id}\n"
        f"👤 Создатель: @{creator.username if creator else 'unknown'}\n"
        f"📌 Тип: {'❤️ Like' if task.task_type == 'like' else '💬 Comment' if task.task_type == 'comment' else '➕ Follow'}\n"
        f"💰 Награда: {task.cost} триксиков\n"
        f"🔗 Ссылки: {task.content[:50]}...\n\n"
        f"📊 Всего заданий: {len(tasks)}"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Выполнить", callback_data=f"lt:perform:{task.task_id}")],
        [InlineKeyboardButton("⏭️ Следующее", callback_data=f"lt:pool_next")],
        [InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def perform_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнить задание"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data.split(":")
    task_id = int(data[2]) if len(data) > 2 else None
    
    if not task_id:
        return
    
    success, message = trix_activity.perform_task(task_id, user_id)
    
    if success:
        keyboard = [
            [InlineKeyboardButton("📋 Еще задания", callback_data="lt:pool")],
            [InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]
        ]
    else:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="lt:pool")]]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============= АДМИН КОМАНДЫ =============

async def liketimeon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включить пользователя в TrixActivity - /liketimeon @user"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только админы")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 Использование: `/liketimeon @username` или `/liketimeon USER_ID`",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    target_user_id = None
    
    if target.startswith('@'):
        username = target[1:]
        for uid, acc in trix_activity.accounts.items():
            if acc.username.lower() == username.lower():
                target_user_id = uid
                break
    elif target.isdigit():
        target_user_id = int(target)
    
    if not target_user_id or target_user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    success, msg = trix_activity.admin_enable_user(target_user_id)
    await update.message.reply_text(msg)

async def liketimeoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключить пользователя в TrixActivity - /liketimeoff @user"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только админы")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 Использование: `/liketimeoff @username`",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    target_user_id = None
    
    if target.startswith('@'):
        username = target[1:]
        for uid, acc in trix_activity.accounts.items():
            if acc.username.lower() == username.lower():
                target_user_id = uid
                break
    elif target.isdigit():
        target_user_id = int(target)
    
    if not target_user_id or target_user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    success, msg = trix_activity.admin_disable_user(target_user_id)
    await update.message.reply_text(msg)

async def trixikiadd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить триксики - /trixikiadd @user 10"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только админы")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 Использование: `/trixikiadd @username КОЛИЧЕСТВО`",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    amount = int(context.args[1]) if context.args[1].isdigit() else 0
    
    if amount <= 0:
        await update.message.reply_text("❌ Укажите положительное число")
        return
    
    target_user_id = None
    if target.startswith('@'):
        username = target[1:]
        for uid, acc in trix_activity.accounts.items():
            if acc.username.lower() == username.lower():
                target_user_id = uid
                break
    
    if not target_user_id or target_user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    success, msg = trix_activity.admin_add_trixiki(target_user_id, amount)
    await update.message.reply_text(msg)

# ============= ЭКСПОРТ =============

__all__ = [
    'liketime_command',
    'handle_lt_callback',
    'handle_lt_text',
    'show_main_menu',
    'balance_command',
    'create_task_menu',
    'handle_create_action',
    'handle_create_input',
    'show_pool',
    'perform_task',
    'liketimeon_command',
    'liketimeoff_command',
    'trixikiadd_command'
]
