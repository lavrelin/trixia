# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Хранилище данных розыгрышей (в продакшене - БД)
giveaway_data = {
    'daypost': [],      # Лучший пост дня
    'daycomment': [],   # Лучший комментарий
    'daytag': [],       # Топ упоминания Трикс
    'weeklyroll': [],   # Еженедельный розыгрыш
    'needtrymore': [],  # Игра NeedTryMore
    'topweek': [],      # Лучший пост недели
    '7tt': [],          # TrixTicket раздача
    'member': [],       # Member розыгрыш
    'trixticket': [],   # TrixTicket конкурс
    'active': [],       # Active3x задание
    'ref': [],          # Рефералы
    'raidtrix': [],     # RaidTrix участники
}

# Шаблон данных для каждой записи
def create_giveaway_record(date: str, winner: str, prize: str, status: str = "Выплачено"):
    return {
        'date': date,
        'winner': winner,
        'prize': prize,
        'status': status  # "Выплачено" / "Пользователь не объявился" / "Отправил на Донат"
    }

async def giveaway_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню розыгрышей"""
    
    keyboard = [
        [
            InlineKeyboardButton("✨24h/Ежедневные", callback_data="giveaway:daily"),
            InlineKeyboardButton("💫7d/Еженедельные", callback_data="giveaway:weekly")
        ],
        [
            InlineKeyboardButton("🌟22th/Ежемесячные", callback_data="giveaway:monthly"),
            InlineKeyboardButton("⚡️Задания", callback_data="giveaway:tasks")
        ],
        [InlineKeyboardButton("↩️ Вернуться", callback_data="menu:back")]
    ]
    
    text = (
    "🥳**GiveAway by BudapestTrix**\n\n"
    "⚡️ Регулярные розыгрыши: **Daily**, **Weekly**, **Monthly** — участвовать легко, шанс победить есть у каждого.\n\n"
    
    "🧮 **Информация:**\n"
    "🪬 Один приз в сутки на участника\n"
    "📛 Фейковые аккаунты в случае победы не получают награду\n"
    "💥 Розыгрыши публикуются с задержкой на день (12.11 → итоги за 11.11)\n"
    "🧬 Победитель получает уведомление в личные сообщения\n\n"
    
    "📁 **Quests** — подработка; делай задания и получай деньги 💴\n\n"
    
    "🐦‍🔥**DAILY** — 🧏🏻‍♀️ 15$ в день\n"
    "🕳️Один пост, коммент, тег @трикс\n\n"
    
    "🐦‍🔥**WEEKLY** — 🧏‍♂️ 55$ в неделю\n"
    "🕳️Roll, NTM, TopWeek, 7TT\n\n"
    
    "🐦‍🔥**MONTHLY** — 🧏🏼 220$+ в месяц\n"
    " 🕳️Member — 100$\n"
    "🎫 TrixTicket — 100$\n"
    "🙅 Каталог услуг — 20$\n"
    
    "💳 Выплата призов — до 24х часов после объявления победителей \n\n"
    
    "👄Анонсы, результаты, информация: [Budapest Partners](https://t.me/budapestpartners)\n"

    )   
await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_tasks_menu(query, context):
    """Меню заданий и монетизации"""
    keyboard = [
        [InlineKeyboardButton("📁 Active3x", callback_data="giveaway:stats:active")],
        [InlineKeyboardButton("🗄️ RaidTrix", callback_data="giveaway:stats:raidtrix")],
        [InlineKeyboardButton("🔏 Реферальные", callback_data="giveaway:stats:ref")],
        [InlineKeyboardButton("↩️ Бэк", callback_data="giveaway:back")]
    ]
    
    text = (
        "🗃️ **Задания & Награды** 🔞\n\n"
        "🧨 **Active3x** — 3$\n"
        "🔥 Подписка на Facebook, Instagram, Threads\n"
        "1️⃣ repost + 10 like + 3 comments\n"
        "❤️‍🔥 Выплата через 3 дня после отправки заявки\n\n"
        "💣 **Trix Raid**\n"
        "Отправляй рекламные сообщения 🌀 Трикс ссылок\n"
        "Используй активные группы Facebook/Telegram сообществ Будапешта и Венгрии:\n"
        "• 26 сообщений — 2$\n"
        "• 35 сообщений — 3$\n"
        "• 44 сообщений — 4$\n"
        "• 50 сообщений — 6$ + 🎫 TrixTicket\n"
        "После выполнения обратитесь к администратору\n\n"
        "🔗 **Рефералы** — 5-10$ + TrixTicket\n"
        "Регистрация + верификация аккаунта Binance: 5$\n"
        "Регистрация + верификация STAKE: 5$ + TrixTicket\n\n"
        "📢 Все результаты: https://t.me/budapestpartners\n"
        "📨 Заявки: @trixilvebot"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_monthly_menu(query, context):
    """Меню ежемесячных розыгрышей"""
    keyboard = [
        [InlineKeyboardButton("🤺 Member", callback_data="giveaway:stats:member")],
        [InlineKeyboardButton("🎫 TrixTicket", callback_data="giveaway:stats:trixticket")],
        [InlineKeyboardButton("🪟 Catalog43X", callback_data="giveaway:stats:catalog43x")],
        [InlineKeyboardButton("🚐 Вернуться", callback_data="giveaway:back")]
    ]
    
    text = (
        "🗽 **ЕЖЕМЕСЯЧНЫЕ РОЗЫГРЫШИ**\n\n"
        "🤺 **Member** — 100$. 🎢 10 категорий — 2 победителя в каждой\n"
        "В конкурсе участвует каждый пользователь, который подписан на Трикса\n\n"
        "🛗 FB группа: [1](https://www.facebook.com/share/g/17gGRpEWS5/?mibextid=wwXIfr), "
        "[2](https://www.facebook.com/share/g/17gGRpEWS5/?mibextid=wwXIfr)\n"
        "🟦 FB друзья: [3](https://www.facebook.com/share/1YAn2biZfQ/?mibextid=wwXIfr), "
        "[4](https://www.facebook.com/share/1BVaDrox47/?mibextid=wwXIfr)\n"
        "🟧 Instagram: [5](https://www.instagram.com/budapesttrix), "
        "[6](https://www.instagram.com/budapesttrix)\n"
        "🌀 Threads: [7](https://www.threads.net/budapesttrix), "
        "[8](https://www.threads.net/budepesttrix)\n"
        "🙅‍♂️ Будапешт канал: [9](https://t.me/snghu), "
        "[10](https://t.me/snghu)\n"
        "🙅‍♀️ Будапешт чат: [11](https://t.me/tgchatxxx), "
        "[12](https://t.me/tgchatxxx)\n"
        "🕵️‍♂️ Куплю/Отдам/Продам: [13](https://t.me/hungarytrade), "
        "[14](https://t.me/hungarytrade)\n"
        "🙅🏻 Каталог услуг (группа): [15](https://t.me/catalogtrix), "
        "[16](https://t.me/catalogtrix)\n"
        "🙅🏼 Каталог услуг (каталог): [17](https://t.me/catalogtrix), "
        "[18](https://t.me/catalogtrix)\n"
        "🐦‍🔥 Budapest Partners: [19](https://t.me/budapestpartners), "
        "[20](https://t.me/budapestpartners)\n\n"
        "🎫 **TrixTicket Конкурс** — Уникальные награды\n"
        "3 победителя из обладателей TrixTicket\n"
        "Призы: билеты на шоу, ваучеры, крипто\n\n"
        "📕 **Catalog43X** — розыгрыш услуги мастера с нашего каталога\n"
        "📒 Мы договариваемся с мастерами, запускаем конкурс\n"
        "📗 Победитель получает бесплатный сеанс\n\n"
        "💳 Выплата USDT в течении суток после получения реквизитов от победителя"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_giveaway_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для розыгрышей"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    section = data[2] if len(data) > 2 else None
    
    if action == "daily":
        await show_daily_menu(query, context)
    elif action == "weekly":
        await show_weekly_menu(query, context)
    elif action == "monthly":
        await show_monthly_menu(query, context)
    elif action == "tasks":
        await show_tasks_menu(query, context)
    elif action == "stats":
        await show_giveaway_stats(query, context, section)
    elif action == "back":
        await giveaway_command(update, context)

async def show_daily_menu(query, context):
    """Меню ежедневных розыгрышей"""
    keyboard = [
        [InlineKeyboardButton("🔲 TopDayPost", callback_data="giveaway:stats:daypost")],
        [InlineKeyboardButton("🔳 TopDayComment", callback_data="giveaway:stats:daycomment")],
        [InlineKeyboardButton("🌀 TopDayTager", callback_data="giveaway:stats:daytag")],
        [InlineKeyboardButton("🏎️ Назад", callback_data="giveaway:back")]
    ]
    
    text = (
        "🏆 **ЕЖЕДНЕВНЫЕ КОНКУРСЫ**\n\n"
        
        "🔲 **TopDayPost** — 5$\n"
        "♥️ Автор лучшего поста дня опубликованого в любом из наших каналов получает 5$\n"
        "💁‍♀️ Предложить /start\n\n"
        
        "🔳 **TopDayComment** — 5$\n"
        "♦️ Автор лучшего комментария получает 5$\n"
        "💁‍♂️(Facebook/Instagram/Threads)\n\n"
        
        "🌀 **TopDayTager** — 5$\n"
        "♠️ Автор лучшего поста, сторис где упоминается Трикс получает 5$\n"
        "💁 Используй /social для ссылок\n\n"
        
        "•Результаты 11-го числа публикуются 12-го❗️"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_weekly_menu(query, context):
    """Меню еженедельных розыгрышей"""
    keyboard = [
        [InlineKeyboardButton("🎲 WeeklyRoll", callback_data="giveaway:stats:weeklyroll")],
        [InlineKeyboardButton("🎳 NeedTryMore", callback_data="giveaway:stats:needtrymore")],
        [InlineKeyboardButton("🪪 TopWeek", callback_data="giveaway:stats:topweek")],
        [InlineKeyboardButton("🎫 7TrixTicket", callback_data="giveaway:stats:7tt")],
        [InlineKeyboardButton("🚂 Назад", callback_data="giveaway:back")]
    ]
    
    text = (
        "📋 **ЕЖЕНЕДЕЛЬНЫЕ РОЗЫГРЫШИ**\n\n"
        
        "🎲 **WeeklyRoll** — 15$ для 3 победителей\n"
        "🫧 Админ запускает конкурс, рандомно определяются победители.\n"
        "⛈️ Каждый получает по 5$ в крипте\n\n"
        
        "🎳 **NeedTryMore** — 30$ для 3 победителей\n"
        "🧑‍🧑‍🧒 Участники используют подсказки, чтобы угадать слово загаданное админом.\n"
        "💨 Первый, кто называет правильный вариант, получает 10$. Три версии игры одновременно\n\n"
        
        "🎩**TopWeek** — 10$\n"
        "👚Автор лучшей публикации за неделю по версии администрации получает 10$\n\n"
        "🎫 **7TrixTicket** — Раздача 7 билетов в неделю\n"
        "🥾Конкурс проводится каждый раз по разному на усмотрение администратора"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def show_monthly_menu(query, context):
    """Меню ежемесячных розыгрышей"""
    keyboard = [
        [InlineKeyboardButton("🤺 Member", callback_data="giveaway:stats:member")],
        [InlineKeyboardButton("🎫 TrixTicket", callback_data="giveaway:stats:trixticket")],
        [InlineKeyboardButton("🪟 Catalog43X", callback_data="giveaway:stats:catalog43x")],
        [InlineKeyboardButton("🚐 Вернуться", callback_data="giveaway:back")]
    ]
    
    text = (
        "🗽 **ЕЖЕМЕСЯЧНЫЕ РОЗЫГРЫШИ**\n\n"
        
        "🤺 **Member** — 100$. 🎢 10 категорий — 2 победителя в каждой\n"
        "В конкурсе участвует каждый пользователь, который подписан на Трикса\n\n"
        
        "🛗 FB группа: [1](https://www.facebook.com/share/g/17gGRpEWS5/?mibextid=wwXIfr), [2](https://www.facebook.com/share/g/17gGRpEWS5/?mibextid=wwXIfr)\n"
        "🟦 FB друзья: [3](https://www.facebook.com/share/1YAn2biZfQ/?mibextid=wwXIfr), [4](https://www.facebook.com/share/1BVaDrox47/?mibextid=wwXIfr)\n"
        "🟧 Instagram: [5](https://www.instagram.com/budapesttrix), [6](https://www.instagram.com/budapesttrix)\n"
        "🌀 Threads: [7](https://www.threads.net/budapesttrix), [8](https://www.threads.net/budepesttrix)\n"
        "🙅‍♂️ Будапешт канал: [9](https://t.me/snghu), [10](https://t.me/snghu)\n"
        "🙅‍♀️ Будапешт чат: [11](https://t.me/tgchatxxx), [12](https://t.me/tgchatxxx)\n"
        "🕵️‍♂️ Куплю/Отдам/Продам: [13](https://t.me/hungarytrade), [14](https://t.me/hungarytrade)\n"
        "🙅🏻 Каталог услуг (участник группы): [15](https://t.me/catalogtrix), [16](https://t.me/catalogtrix)\n"
        "🙅🏼 Каталог услуг (участник каталога): [17](https://t.me/catalogtrix), [18](https://t.me/catalogtrix)\n"
        "🐦‍🔥 Budapest Partners: [19](https://t.me/budapestpartners), [20](https://t.me/budapestpartners)\n\n"
        
        "🎫 **TrixTicket Конкурс** — Уникальные награды\n"
        "3 победителя из обладателей TrixTicket\n"
        "Призы: билеты на шоу, ваучеры, крипто\n\n"
        
        "📕**Catalog43X** — розыгрыш услуги мастера с нашего каталога\n"
        "📒 Мы договариваемся с мастерами, запускаем конкурс, победитель получает бесплатный сеанс\n"
        "📗 Условия: в доработке 💤\n\n"
        "💳 Выплата USDT в течении суток после получения реквизитов от победителя"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_tasks_menu(query, context):
    """Меню заданий и монетизации"""
    keyboard = [
        [InlineKeyboardButton("📁 Active3x", callback_data="giveaway:stats:active")],
        [InlineKeyboardButton("🗄️ RaidTrix", callback_data="giveaway:stats:raidtrix")],
        [InlineKeyboardButton("🔏 Реферальные", callback_data="giveaway:stats:ref")],
        [InlineKeyboardButton("↩️ Бэк", callback_data="giveaway:back")]
    ]
    
    text = (
        "🗃️**Задания&Награды**🔞\n\n"
        
        "•🧨 **Active3x** — 3$\n"
        "•🔥 Подписка на Facebook, Instagram, Threads\n"
        "+1️⃣ repost + 10 like + 3 comments\n"
        "•❤️‍🔥Выплата через 3 дня после отправки заявки.\n\n"
        
        "💣**Trix Raid**\n"
    "Отправляй рекламные сообщения 🌀Трикс ссылок\n"
    "Используй активные группы Facebook/Telegram сообществ Будапешта и Венгрии:\n"
    "• 26 сообщений — 2$\n"
    "• 35 сообщений — 3$\n"
    "• 44 сообщений — 4$\n"
    "• 50 сообщений — 6$ + 🎫 TrixTicket \n"
    "После выполнения обратитесь к администратору"
        
        "🔗 **Рефералы** — 5$ + TrixTicket\n"
        "Регистрация + верификация аккаунта Binance: 5$\n"
        "Регистрация + верификация STAKE: 5$ + TrixTicket\n\n"
        
        "📢 Все результаты: https://t.me/budapestpartners\n"
        "📨 Заявки: @trixilvebot"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_giveaway_stats(query, context, section: str):
    """Показать статистику конкретного розыгрыша"""
    
    if section not in giveaway_data:
        await query.answer("❌ Раздел не найден", show_alert=True)
        return
    
    records = giveaway_data[section]
    
    # Названия разделов
    section_names = {
        'daypost': '🏆 TopDayPost',
        'daycomment': '🗣️ TopDayComment',
        'daytag': '🌀 TopDayTager',
        'weeklyroll': '🎲 WeeklyRoll',
        'needtrymore': '🎮 NeedTryMore',
        'topweek': '⭐️ TopWeek',
        '7tt': '🎫 7TrixTicket',
        'member': '👥 Member',
        'trixticket': '🎫 TrixTicket',
        'active': '🟢 Active3x',
        'ref': '🔗 Рефералы',
        'raidtrix': '💬 RaidTrix',
    }
    
    title = section_names.get(section, section)
    
    # Формируем текст со статистикой
    if not records:
        text = f"📊 **{title}**\n\n❌ Еще нет записей"
    else:
        text = f"📊 **{title}** (Всего: {len(records)})\n\n"
        
        for record in records[-10:]:  # Показываем последние 10
            text += (
                f"📅 {record['date']}\n"
                f"👤 @{record['winner']}\n"
                f"🎁 {record['prize']}\n"
                f"✅ {record['status']}\n\n"
            )
    
    # Итоговая сумма
    total_sum = 0
    for record in records:
        try:
            # Извлекаем числовое значение из приза (например, "5$" -> 5)
            prize_str = record['prize'].replace('$', '').strip()
            if prize_str.isdigit():
                total_sum += int(prize_str)
        except:
            pass
    
    if total_sum > 0:
        text += f"\n💰 **Общая сумма выплат: ${total_sum}**"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="giveaway:back")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

text = (
    "🪬 **#P2P ПРОДАТЬ/КУПИТЬ КРИПТУ**\n\n"
    
    "💡 **Как быстро продать крипту и получить деньги на карту?**\n\n"
    
    "🔗 Пример: Binance → Monobank\n"
    "💱 Пара: USDT / UAH 💸\n\n"
    
    "1️⃣ **Зарегистрируй аккаунт**\n"
    "[🌐 BINANCE](https://accounts.binance.com/en/register?ref=TRIXBONUS)\n"
    "✅ Подтверди почту и телефон ✉️📲\n\n"
    
    "2️⃣ **Пройди верификацию**\n"
    "🧾 Подтверди личность для P2P\n"
    "⏱️ Обычно занимает 5–10 минут\n\n"
    
    "3️⃣ **Добавь карту Monobank**\n"
    "💳 Путь: P2P → Платёжные методы → Добавить карту\n"
    "📝 ФИО должно совпадать с Binance!\n\n"
    
    "4️⃣ **Продай крипту**\n"
    "🔁 Открой P2P → Продать\n"
    "Выбери:\n"
    "• Монета: USDT 🪙\n"
    "• Валюта: UAH 💵\n"
    "• Оплата: Monobank 💳\n\n"
    
    "🔍 **Выбери покупателя с рейтингом 98%+** ⭐\n"
    "✅ Нажми «Продать USDT»\n\n"
    
    "5️⃣ **Получение денег** 💰\n"
    "💳 Покупатель переведет средства на карту\n"
    "✅ Подтверди «Оплату получил»\n\n"
    
    "⚡️ **Готово!**\n"
    "✅ Деньги у тебя\n"
    "🔒 Крипта уходит покупателю\n\n"
    
    "📞 Вопросы или помощь? Пиши: @trixilvebot"
)
    
    keyboard = [
        [InlineKeyboardButton("🔙 Главное меню", callback_data="menu:back")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# Функция для добавления записей (для админа)
async def add_giveaway_record(section: str, winner: str, prize: str, status: str = "Выплачено"):
    """Добавить запись о победителе"""
    if section not in giveaway_data:
        return False
    
    date = datetime.now().strftime("%d.%m.%y")
    record = create_giveaway_record(date, winner, prize, status)
    giveaway_data[section].append(record)
    logger.info(f"Added giveaway record: {section} - {winner} - {prize}")
    return True

__all__ = [
    'giveaway_command',
    'handle_giveaway_callback',
    'p2p_command',
    'add_giveaway_record',
    'giveaway_data'
]
