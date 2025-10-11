# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
from services.admin_notifications import admin_notifications
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

# Доступные номера билетов
AVAILABLE_TICKET_NUMBERS = [
    351040, 613030, 963320, 562316, 500099, 339945, 994245, 200056, 910076, 848652,
    768949, 765348, 198069, 880494, 970386, 291047, 872367, 748455, 443895, 352887,
    218048, 957039, 363137, 123755, 450752, 376250, 626234, 895236, 465918, 727809,
    246560, 864159, 642001, 502213, 261482, 999907, 12361, 181194, 467349, 264777, 
    365423, 171197, 304592, 369195, 996793, 727476, 562749, 761685, 368169, 454956, 
    535181, 488012, 805118, 89772, 159521, 909078, 116861, 232871, 714047, 347559, 
    15449, 956328, 668625, 999187, 298527, 8258, 904956, 959776, 376971, 764376, 
    181869, 901139, 618963, 168459, 262445, 301595, 756483, 880629, 108248, 114764, 
    125456, 943557, 710780, 244229, 49875, 909249, 743649, 278646, 676851, 941118, 
    552515, 843233, 115439, 879847, 26906, 40450, 855212, 1020, 952494, 403637, 
    691061, 233375, 854871
]

# Хранилище данных TrixTicket
trixticket_data = {
    'holders': {},  # {user_id: {'username': str, 'ticket_number': int, 'obtained_at': str}}
    'winners': [],  # История победителей [{user_id, username, prize, date}]
    'used_numbers': set(),  # Использованные номера
    'next_draw': '01.12.2025'  # Дата следующего розыгрыша
}

async def tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о TrixTicket и участниках"""
    
    total_holders = len(trixticket_data['holders'])
    
    keyboard = [
        [InlineKeyboardButton("👤 Мой билет", callback_data="tt:myticket")],
        [InlineKeyboardButton("🏆 Победители", callback_data="tt:winners")],
        [InlineKeyboardButton("📋 Как получить", callback_data="tt:howto")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="menu:back")]
    ]
    
    text = (
        "🎫 **TRIXTICKET - ЕЖЕМЕСЯЧНЫЙ РОЗЫГРЫШ**\n\n"
        
        "📌 **Описание:**\n"
        "Цифровой билет для участия в ежемесячном розыгрыше\n"
        "Победители получают ценные призы!\n\n"
        
        "👥 **Текущие участники:** {}\n"
        "🎰 **Следующий розыгрыш:** {}\n\n"
        
        "🎁 **Предыдущие победители:**\n"
    ).format(total_holders, trixticket_data['next_draw'])
    
    # Показываем последних 3 победителей
    if trixticket_data['winners']:
        for winner in trixticket_data['winners'][-3:]:
            text += f"• @{winner['username']} — {winner['prize']}\n"
    else:
        text += "• Еще нет победителей\n"
    
    text += (
        "\n📋 **Правила:**\n"
        "• 1 билет максимум на пользователя\n"
        "• Фейковые аккаунты не участвуют\n"
        "• Выплата в течение 24 часов\n\n"
        
        "💡 **Нажмите кнопку ниже для подробности:**"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def myticket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверить наличие билета у пользователя"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"ID_{user_id}"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="tt:back")]]
    
    if user_id in trixticket_data['holders']:
        ticket_info = trixticket_data['holders'][user_id]
        text = (
            f"🎫 **ВАШ БИЛЕТ**\n\n"
            f"✅ У вас есть билет!\n"
            f"🎟️ Номер: {ticket_info['ticket_number']}\n"
            f"📅 Получен: {ticket_info['obtained_at']}\n"
            f"🎰 Участвуете в розыгрыше: {trixticket_data['next_draw']}\n\n"
            f"🍀 Удачи!"
        )
    else:
        text = (
            f"❌ **НЕТ БИЛЕТА**\n\n"
            f"У вас пока нет TrixTicket\n\n"
            f"📌 **Как получить:**\n"
            f"• Выигрыши в конкурсах\n"
            f"• Выполнить задания через /trixmoney\n"
            f"• Получить от администрации\n\n"
            f"💡 Нажмите 'Назад' для подробности"
        )
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def trixtickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список победителей"""
    
    text = "🏆 **ИСТОРИЯ ПОБЕДИТЕЛЕЙ TRIXTICKET**\n\n"
    
    if not trixticket_data['winners']:
        text += "❌ Еще нет победителей"
    else:
        for i, winner in enumerate(trixticket_data['winners'], 1):
            text += (
                f"{i}. **@{winner['username']}**\n"
                f"   📅 Дата: {winner['date']}\n"
                f"   🎁 Приз: {winner['prize']}\n\n"
            )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="tt:back")]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_trixticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для TrixTicket"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    
    if action == "myticket":
        await myticket_command(update, context)
    elif action == "winners":
        await trixtickets_command(update, context)
    elif action == "howto":
        await show_howto(query, context)
    elif action == "back":
        await tickets_command(update, context)

async def show_howto(query, context):
    """Как получить TrixTicket"""
    
    text = (
        "📌 **КАК ПОЛУЧИТЬ TRIXTICKET**\n\n"
        
        "1️⃣ **Выигрыши в конкурсах:**\n"
        "• WeeklyRoll — автоматически получите\n"
        "• NeedTryMore — победители получают\n"
        "• 7TT раздача — прямая раздача\n\n"
        
        "2️⃣ **Выполнить задания:**\n"
        "• Active3x выполнение — 0 TrixTicket\n"
        "• RaidTrix (50 сообщений) — +1 TrixTicket\n"
        "• Ref (STAKE верификация) — +1 TrixTicket\n"
        "Используйте /trixmoney\n\n"
        
        "3️⃣ **Подарок от администрации:**\n"
        "• За активность в сообществе\n"
        "• За помощь другим участникам\n"
        "• Специальные акции\n\n"
        
        "🎰 **РОЗЫГРЫШ:**\n"
        f"📅 Дата: {trixticket_data['next_draw']}\n"
        "🏆 Будут выбраны 3 случайных победителя\n"
        "🎁 Призы: билеты на шоу, ваучеры, крипто\n\n"
        
        "💡 Вопросы? @trixilvebot"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="tt:back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============= АДМИН КОМАНДЫ =============

async def givett_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдать билет пользователю - /givett <user_id>"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "📝 Использование: `/givett 123456789`",
            parse_mode='Markdown'
        )
        return
    
    user_id = int(context.args[0])
    
    if user_id in trixticket_data['holders']:
        await update.message.reply_text(f"❌ У пользователя {user_id} уже есть билет!")
        return
    
    if not trixticket_data['used_numbers']:
        # Инициализируем использованные номера
        trixticket_data['used_numbers'] = set()
    
    # Находим первый неиспользованный номер
    ticket_number = None
    for num in AVAILABLE_TICKET_NUMBERS:
        if num not in trixticket_data['used_numbers']:
            ticket_number = num
            break
    
    if ticket_number is None:
        await update.message.reply_text("❌ Все билеты закончились!")
        return
    
    # Добавляем билет
    trixticket_data['holders'][user_id] = {
        'username': f"user_{user_id}",
        'ticket_number': ticket_number,
        'obtained_at': datetime.now().strftime("%d.%m.%Y")
    }
    trixticket_data['used_numbers'].add(ticket_number)
    
    await update.message.reply_text(
        f"✅ **Билет выдан!**\n\n"
        f"👤 User ID: {user_id}\n"
        f"🎟️ Номер билета: {ticket_number}\n"
        f"👥 Всего участников: {len(trixticket_data['holders'])}"
    )
    
    logger.info(f"Ticket {ticket_number} given to user {user_id}")

async def removett_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Убрать билет у пользователя - /removett <user_id>"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "📝 Использование: `/removett 123456789`",
            parse_mode='Markdown'
        )
        return
    
    user_id = int(context.args[0])
    
    if user_id not in trixticket_data['holders']:
        await update.message.reply_text("❌ У пользователя нет билета!")
        return
    
    ticket_num = trixticket_data['holders'][user_id]['ticket_number']
    del trixticket_data['holders'][user_id]
    # НЕ удаляем номер из used_numbers - он использован
    
    await update.message.reply_text(
        f"✅ **Билет удален!**\n\n"
        f"👤 User ID: {user_id}\n"
        f"🎟️ Номер: {ticket_num}\n"
        f"👥 Осталось участников: {len(trixticket_data['holders'])}"
    )

async def userstt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать всех пользователей с билетами - /userstt"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not trixticket_data['holders']:
        await update.message.reply_text("❌ Нет участников")
        return
    
    text = "🎫 **СПИСОК УЧАСТНИКОВ TRIXTICKET**\n\n"
    
    for user_id, info in trixticket_data['holders'].items():
        text += (
            f"👤 User ID: {user_id}\n"
            f"🎟️ Билет: {info['ticket_number']}\n"
            f"📅 Дата: {info['obtained_at']}\n\n"
        )
    
    text += f"📊 **Всего: {len(trixticket_data['holders'])} участников**"
    
    await update.message.reply_text(text)

async def trixticketstart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запустить розыгрыш - /trixticketstart"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if len(trixticket_data['holders']) < 3:
        await update.message.reply_text(
            f"❌ Недостаточно участников!\n"
            f"Есть: {len(trixticket_data['holders'])}\n"
            f"Нужно: минимум 3"
        )
        return
    
    # Выбираем 3 случайных победителя
    winners_list = random.sample(
        list(trixticket_data['holders'].items()), 
        min(3, len(trixticket_data['holders']))
    )
    
    # Сохраняем текущих победителей для /ttrenumber
    context.user_data['current_tt_winners'] = winners_list
    
    text = "🎰 **РОЗЫГРЫШ TRIXTICKET ПРОВЕДЕН!**\n\n"
    text += "🏆 **Случайно выбраны 3 победителя:**\n\n"
    
    for i, (user_id, info) in enumerate(winners_list, 1):
        text += (
            f"{i}. 👤 @{info['username']} (ID: {user_id})\n"
            f"   🎟️ Билет: {info['ticket_number']}\n\n"
        )
    
    text += (
        "📝 **Далее:**\n"
        "1. Свяжитесь с победителями\n"
        "2. Используйте /ttrenumber если нужна замена\n"
        "3. Используйте /ttsave для сохранения результатов"
    )
    
    await update.message.reply_text(text)
    logger.info(f"TrixTicket draw executed with {len(winners_list)} winners")

async def ttrenumber_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переизбрать одного победителя - /ttrenumber "123456"
    Оставляет двоих, выбирает нового вместо указанного"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 Использование: `/ttrenumber \"123456\"`\n"
            "Укажите номер билета для замены",
            parse_mode='Markdown'
        )
        return
    
    ticket_to_replace = int(context.args[0])
    current_winners = context.user_data.get('current_tt_winners', [])
    
    if not current_winners:
        await update.message.reply_text("❌ Сначала запустите розыгрыш /trixticketstart")
        return
    
    # Находим победителя с этим номером
    winner_index = None
    for i, (user_id, info) in enumerate(current_winners):
        if info['ticket_number'] == ticket_to_replace:
            winner_index = i
            break
    
    if winner_index is None:
        await update.message.reply_text(f"❌ Билет {ticket_to_replace} не найден в списке победителей")
        return
    
    # Выбираем нового победителя из оставшихся участников
    remaining_users = [
        (uid, info) for uid, info in trixticket_data['holders'].items()
        if uid not in [w[0] for w in current_winners]
    ]
    
    if not remaining_users:
        await update.message.reply_text("❌ Нет других участников для замены")
        return
    
    new_winner = random.choice(remaining_users)
    current_winners[winner_index] = new_winner
    context.user_data['current_tt_winners'] = current_winners
    
    text = f"✅ **Победитель заменен!**\n\n"
    text += f"❌ Удален: {ticket_to_replace}\n"
    text += f"✅ Добавлен: @{new_winner[1]['username']} (Билет: {new_winner[1]['ticket_number']})\n\n"
    text += "📋 **Новые победители:**\n"
    
    for i, (user_id, info) in enumerate(current_winners, 1):
        text += f"{i}. @{info['username']} (Билет: {info['ticket_number']})\n"
    
    await update.message.reply_text(text)

async def ttsave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить результаты розыгрыша - /ttsave"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    current_winners = context.user_data.get('current_tt_winners', [])
    
    if not current_winners:
        await update.message.reply_text("❌ Нет текущих результатов розыгрыша")
        return
    
    date = datetime.now().strftime("%d.%m.%Y")
    
    # Сохраняем в историю
    for user_id, info in current_winners:
        winner_record = {
            'user_id': user_id,
            'username': info['username'],
            'date': date,
            'prize': 'TrixTicket приз'  # Нужно уточнить приз
        }
        trixticket_data['winners'].append(winner_record)
    
    # Очищаем текущих победителей
    context.user_data['current_tt_winners'] = []
    
    text = f"✅ **Результаты сохранены!**\n\n"
    text += f"📊 Сохранено {len(current_winners)} победителей\n"
    text += f"📅 Дата: {date}\n\n"
    text += "🔔 Результаты добавлены в /trixtickets"
    
    await update.message.reply_text(text)
    
    # Отправляем уведомление в админскую группу
    try:
        await admin_notifications.send_message(
            f"✅ TrixTicket розыгрыш сохранен\n"
            f"📊 Победителей: {len(current_winners)}\n"
            f"📅 Дата: {date}"
        )
    except:
        pass

async def trixticketclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полная очистка всех данных TrixTicket - /trixticketclear"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    
    # Подтверждение
    if context.args and context.args[0] == "confirm":
        # Очищаем все
        trixticket_data['holders'] = {}
        trixticket_data['winners'] = []
        trixticket_data['used_numbers'] = set()
        context.user_data['current_tt_winners'] = []
        
        await update.message.reply_text(
            "⚠️ **ПОЛНАЯ ОЧИСТКА ВЫПОЛНЕНА!**\n\n"
            "✅ Все билеты удалены\n"
            "✅ История очищена\n"
            "✅ Участники удалены\n\n"
            "Система готова к новому циклу"
        )
        
        logger.warning("TrixTicket data completely cleared")
        return
    
    # Запрос подтверждения
    text = (
        "⚠️ **ВНИМАНИЕ: ПОЛНАЯ ОЧИСТКА TRIXTICKET**\n\n"
        "Это удалит:\n"
        "❌ Все билеты участников\n"
        "❌ Историю победителей\n"
        "❌ Все номера\n\n"
        "Введите `/trixticketclear confirm` для подтверждения"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')

__all__ = [
    'tickets_command',
    'myticket_command',
    'trixtickets_command',
    'handle_trixticket_callback',
    'givett_command',
    'removett_command',
    'userstt_command',
    'trixticketstart_command',
    'ttrenumber_command',
    'ttsave_command',
    'trixticketclear_command',
    'trixticket_data'
]
