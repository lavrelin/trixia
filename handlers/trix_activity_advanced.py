# -*- coding: utf-8 -*-
"""
TrixActivity - Продвинутые функции
Подтверждение заданий, подписки, статистика
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
import logging
from datetime import datetime

from handlers.trix_activity_service import trix_activity
from services.admin_notifications import admin_notifications

logger = logging.getLogger(__name__)

# ============= СТАТИСТИКА =============

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику TrixActivity"""
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await update.message.reply_text("❌ Используйте /liketime")
        return
    
    # Получаем топ пользователей
    top_users = trix_activity.get_top_users(5)
    stats = trix_activity.get_task_stats()
    
    text = "📊 **СТАТИСТИКА TRIXACTIVITY**\n\n"
    
    text += "🏆 **ТОП-5 ПОЛЬЗОВАТЕЛЕЙ:**\n"
    for i, (username, balance, max_balance) in enumerate(top_users, 1):
        text += f"{i}. @{username}: {balance}/{max_balance} 💰\n"
    
    text += f"\n📈 **СТАТИСТИКА ЗАДАНИЙ:**\n"
    text += f"• Активных: {stats['active']}\n"
    text += f"• Завершено: {stats['completed']}\n"
    text += f"• В спорах: {stats['disputed']}\n"
    text += f"• Всего: {stats['total']}\n"
    text += f"• Ожидают подтверждения: {stats['pending_confirmations']}\n\n"
    
    text += "**По типам:**\n"
    for task_type, count in stats['by_type'].items():
        emoji = {'like': '❤️', 'comment': '💬', 'follow': '➕'}.get(task_type, '📌')
        text += f"• {emoji} {task_type}: {count}\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============= УПРАВЛЕНИЕ ФУНКЦИЯМИ =============

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления функциями"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await query.answer("❌ Используйте /liketime", show_alert=True)
        return
    
    account = trix_activity.accounts[user_id]
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'✅' if account.active_functions['like'] else '❌'} Like",
                callback_data="lt:toggle:like"
            ),
            InlineKeyboardButton(
                f"{'✅' if account.active_functions['comment'] else '❌'} Comment",
                callback_data="lt:toggle:comment"
            )
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if account.active_functions['follow'] else '❌'} Follow",
                callback_data="lt:toggle:follow"
            )
        ],
        [InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]
    ]
    
    text = (
        f"⚙️ **УПРАВЛЕНИЕ ФУНКЦИЯМИ**\n\n"
        f"✅ - функция включена (создавай задания)\n"
        f"❌ - функция отключена (не можешь создавать)\n\n"
        
        f"📌 Выбери функцию чтобы переключить"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def toggle_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить функцию"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data.split(":")
    func_name = data[2] if len(data) > 2 else None
    
    if user_id not in trix_activity.accounts or not func_name:
        return
    
    account = trix_activity.accounts[user_id]
    current_state = account.active_functions.get(func_name, True)
    account.active_functions[func_name] = not current_state
    
    new_state = "✅ включена" if account.active_functions[func_name] else "❌ отключена"
    
    await query.answer(f"Функция {func_name}: {new_state}")
    
    # Обновляем меню
    await settings_menu(update, context)

# ============= ПРОВЕРКА ПОДПИСОК =============

async def subscribe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню проверки подписок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await query.answer("❌ Используйте /liketime", show_alert=True)
        return
    
    account = trix_activity.accounts[user_id]
    
    if account.max_balance >= 20:
        text = (
            "✅ **ВЫ УЖЕ НА МАКСИМУМЕ!**\n\n"
            "🎯 Максимальный лимит: 20 триксиков\n\n"
            "Спасибо за поддержку TrixActivity! 🙏"
        )
        keyboard = [[InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]]
    else:
        text = (
            "📱 **УВЕЛИЧИТЬ ЛИМИТ ДО 20 ТРИКСИКОВ**\n\n"
            "🎯 Требуется проверка подписок:\n\n"
            "✅ Подпишитесь на:\n"
            "  • Instagram: @budapesttrix\n"
            "  • Threads: @budapesttrix\n\n"
            "📝 После подписки нажмите кнопку ниже"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Проверить подписки", callback_data="lt:verify_subs")],
            [InlineKeyboardButton("🔗 Instagram", url="https://instagram.com/budapesttrix")],
            [InlineKeyboardButton("🌀 Threads", url="https://threads.net/@budapesttrix")],
            [InlineKeyboardButton("◀️ Меню", callback_data="lt:menu")]
        ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def verify_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос проверки подписок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in trix_activity.accounts:
        await query.answer("❌ Используйте /liketime", show_alert=True)
        return
    
    account = trix_activity.accounts[user_id]
    
    success, message = trix_activity.request_subscription_check(user_id)
    
    # Отправляем уведомление админам
    try:
        admin_msg = (
            f"📱 **ПРОВЕРКА ПОДПИСОК**\n\n"
            f"👤 Пользователь: @{account.username} (ID: {user_id})\n"
            f"🔗 Instagram: @{account.instagram or 'не указан'}\n"
            f"🌀 Threads: @{account.threads or 'не указан'}\n\n"
            f"📋 Требуется проверить подписку на:\n"
            f"  • Instagram @budapesttrix\n"
            f"  • Threads @budapesttrix\n\n"
            f"📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"lt:approve_sub:{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"lt:reject_sub:{user_id}")
            ]
        ]
        
        await context.bot.send_message(
            chat_id=Config.ADMIN_GROUP_ID,
            text=admin_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending subscription check to admin: {e}")
    
    await query.edit_message_text(message, parse_mode='Markdown')

async def approve_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ одобрил подписку"""
    query = update.callback_query
    await query.answer()
    
    if not Config.is_admin(update.effective_user.id):
        await query.answer("❌ Только админы", show_alert=True)
        return
    
    data = query.data.split(":")
    user_id = int(data[2]) if len(data) > 2 else None
    
    if not user_id or user_id not in trix_activity.accounts:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    success, msg = trix_activity.admin_increase_limit(user_id)
    
    if success:
        # Уведомляем пользователя
        account = trix_activity.accounts[user_id]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ **ПОДПИСКИ ОДОБРЕНЫ!**\n\n"
                    f"🎉 Ваш лимит триксиков увеличен до 20!\n\n"
                    f"💰 Максимальный баланс: 20 триксиков\n\n"
                    f"Спасибо за поддержку TrixActivity! 🙏"
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
    
    await query.edit_message_text(f"✅ {msg}")

async def reject_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ отклонил подписку"""
    query = update.callback_query
    await query.answer()
    
    if not Config.is_admin(update.effective_user.id):
        await query.answer("❌ Только админы", show_alert=True)
        return
    
    data = query.data.split(":")
    user_id = int(data[2]) if len(data) > 2 else None
    
    if not user_id:
        return
    
    # Уведомляем пользователя
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ **ПОДПИСКИ НЕ ПОДТВЕРЖДЕНЫ**\n\n"
                f"⚠️ Убедитесь, что вы подписаны на:\n"
                f"  • Instagram @budapesttrix\n"
                f"  • Threads @budapesttrix\n\n"
                f"Попробуйте еще раз позже!"
            ),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error notifying user: {e}")
    
    await query.edit_message_text("❌ Запрос отклонен")

# ============= ПОДТВЕРЖДЕНИЕ ЗАДАНИЙ =============

async def confirm_pending_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню подтверждения задания"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Находим ожидающие подтверждения
    pending = []
    for task_id, conf in trix_activity.pending_confirmations.items():
        if conf['creator_id'] == user_id:
            pending.append((task_id, conf))
    
    if not pending:
        await query.answer("❌ Нет ожидающих подтверждений", show_alert=True)
        return
    
    task_id, conf = pending[0]
    task = trix_activity.tasks.get(task_id)
    performer = trix_activity.accounts.get(conf['performer_id'])
    
    if not task or not performer:
        await query.answer("❌ Информация не найдена", show_alert=True)
        return
    
    text = (
        f"📋 **ПОДТВЕРЖДЕНИЕ ЗАДАНИЯ #{task_id}**\n\n"
        f"👤 Исполнитель: @{performer.username}\n"
        f"📌 Тип: {'❤️ Like' if task.task_type == 'like' else '💬 Comment' if task.task_type == 'comment' else '➕ Follow'}\n"
        f"💰 Награда: {task.cost} триксиков\n\n"
        f"⏳ Осталось: {int((conf['deadline'] - datetime.now()).total_seconds() // 60)} минут\n\n"
        f"✅ - подтвердить выполнение\n"
        f"❌ - отклонить и отправить на проверку админов"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"lt:confirm:{task_id}:approve"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"lt:confirm:{task_id}:reject")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def process_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать подтверждение задания"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data.split(":")
    task_id = int(data[2]) if len(data) > 2 else None
    action = data[3] if len(data) > 3 else None
    
    if not task_id or not action:
        return
    
    task = trix_activity.tasks.get(task_id)
    
    if not task or task.creator_id != user_id:
        await query.answer("❌ Это не ваше задание", show_alert=True)
        return
    
    success, message = trix_activity.confirm_task(
        task_id,
        user_id,
        approve=(action == "approve")
    )
    
    if success and action == "reject":
        # Отправляем в админ-группу
        performer = trix_activity.accounts.get(task.performer_id)
        report = trix_activity.admin_dispute_report(task_id)
        
        try:
            await context.bot.send_message(
                chat_id=Config.ADMIN_GROUP_ID,
                text=report,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending dispute report: {e}")
    
    await query.edit_message_text(message, parse_mode='Markdown')

# ============= ЭКСПОРТ =============

__all__ = [
    'stats_command',
    'settings_menu',
    'toggle_function',
    'subscribe_menu',
    'verify_subscriptions',
    'approve_subscription',
    'reject_subscription',
    'confirm_pending_task',
    'process_confirmation'
]
