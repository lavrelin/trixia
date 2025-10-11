# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def social_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать социальные сети TRIX"""
    
    keyboard = [
        [InlineKeyboardButton("🧢 Instagram", url="https://www.instagram.com/budapesttrix?igsh=ZXlrNmo4NDdyN2Vz&utm_source=qr")],
        [InlineKeyboardButton("🔷 Facebook Group", url="https://www.facebook.com/share/g/1EKwURtZ13/?mibextid=wwXIfr")],
        [InlineKeyboardButton("🌀 Threads", url="https://www.threads.com/@budapesttrix?igshid=NTc4MTIwNjQ2YQ==")],
        [InlineKeyboardButton("💎 Telegram DM", url="https://t.me/trixilvebot")],
        [InlineKeyboardButton("🔦 Главное", callback_data="menu:back")]
    ]
    
    text = (
        "🩵 **СОЦИАЛЬНЫЕ СЕТИ TRIX**\n\n"
        "Присоединяйтесь к нам в социальных сетях:\n\n"
        
        "🧢 **Instagram**\n"
        "Взаимодействие с подписчиками\n"
    
        
        "🔷 **Facebook**\n"
        "Дублирование контента с каналов\n\n"
        
        "🌀 **Threads**\n"
        "Мысли, флуд\n"

        
        "💙 **Telegram DM**\n"
        "Предложения, жалобы, выплаты с розыгрышей. \n\n"
        
        "🥿 Нажмите на кнопку чтобы перейти"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def giveaway_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о розыгрышах"""

    keyboard = [
        [InlineKeyboardButton("🫦 Полная информация", url="https://t.me/budapestpartners")],
        [InlineKeyboardButton("👄 Канал с розыгрышами", url="https://t.me/budapestpartners")],
        [InlineKeyboardButton("👅 Главное меню", callback_data="menu:back")]
    ]

    text = (
        "🔋 **СИСТЕМА РОЗЫГРЫШЕЙ TRIX**\n\n"
        "🧖 **Ежедневно**\n"
        "• TopDayPost — лучший пост дня (5 $)\n"
        "• TopDayComment — лучший комментарий дня (5 $)\n"
        "📊 /daypost • /daycomment\n\n"
        
        "🧖‍♂️ **Еженедельно**\n"
        "• WeeklyRoll — 3 случайных победителя по 5 $\n"
        "• NeedTryMore — угадай слово, 3 победителя по 10 $\n"
        "• TopWeek — лучший пост недели (10 $)\n"
        "• 7TT — выдача 7 TrixTicket\n"
        "📊 /weeklyroll • /needtrymore • /topweek • /7tt\n\n"
        
        "🧖‍♀️ **Ежемесячно**\n"
        "• Member — раздача 100 $ среди участников сообществ\n"
        "• TrixTicket — розыгрыш среди обладателей TrixTicket\n"
        "📊 /member • /trixtickets\n\n"
        
        "💡 **Правила**\n"
        "• Один человек может выиграть только в одном конкурсе\n"
        "• Фейковые аккаунты исключаются\n"
        "• Выплаты — в USDT в течение 24 ч\n\n"
        
        "💎 **/trixmoney** — выполняй задания, зарабатывай $ и получай бонусы\n\n"
        
        "🎲 Используй каждый шанс"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


__all__ = ['social_command', 'giveaway_command']
