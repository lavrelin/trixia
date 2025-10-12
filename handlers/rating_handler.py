# -*- coding: utf-8 -*-
"""
Система рейтинга с опросами
Голоса конвертируются в очки и агрегируются по профилю и полу
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from config import Config
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# ============= ХРАНИЛИЩЕ ДАННЫХ =============

rating_data = {
    'posts': {},  # {post_id: {'profile_url': str, 'gender': str, 'photo_file_id': str, 'caption': str, 'votes': {}}}
    'profiles': {},  # {profile_url: {'gender': str, 'total_score': int, 'vote_count': int, 'post_ids': []}}
    'user_votes': {}  # {(user_id, post_id): vote_value}  <- для отслеживания повторных голосов
}

# ============= ОСНОВНЫЕ КОМАНДЫ =============

async def rate_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс публикации фото с опросом - /ratestart"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только админы могут создавать опросы")
        return
    
    context.user_data['rate_step'] = 'photo'
    
    keyboard = [[InlineKeyboardButton("🚗 Отмена", callback_data="rate:cancel")]]
    
    text = (
        "📊 **СОЗДАНИЕ РЕЙТИНГА С ОПРОСОМ**\n\n"
        "Шаг 1️⃣ из 3️⃣\n\n"
        "📸 Отправьте фотографию"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    context.user_data['waiting_for'] = 'rate_photo'

async def handle_rate_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото для опроса"""
    if not update.message.photo:
        await update.message.reply_text("❌ Отправьте фотографию")
        return
    
    context.user_data['rate_photo_file_id'] = update.message.photo[-1].file_id
    context.user_data['rate_step'] = 'profile'
    context.user_data['waiting_for'] = 'rate_profile'
    
    keyboard = [[InlineKeyboardButton("🔙 Вернуться", callback_data="rate:back")]]
    
    text = (
        "✅ Фото получено!\n\n"
        "Шаг 2️⃣ из 3️⃣\n\n"
        "🔗 Отправьте ссылку на профиль или username (Instagram, Telegram и т.д.)\n"
        "Пример: @username или https://instagram.com/username"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_rate_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка профиля"""
    profile_url = update.message.text.strip()
    
    if not profile_url or len(profile_url) < 3:
        await update.message.reply_text("❌ Неверный формат ссылки")
        return
    
    # Нормализуем URL
    if profile_url.startswith('@'):
        profile_url = profile_url[1:]
    elif not profile_url.startswith('http'):
        profile_url = f"@{profile_url}"
    
    context.user_data['rate_profile'] = profile_url
    context.user_data['rate_step'] = 'gender'
    context.user_data['waiting_for'] = None
    
    keyboard = [
        [
            InlineKeyboardButton("🧑‍🦱 Boy", callback_data="rate:gender:boy"),
            InlineKeyboardButton("👱‍♀️ Girl", callback_data="rate:gender:girl")
        ],
        [
            InlineKeyboardButton("❓ Unknown", callback_data="rate:gender:unknown"),
            InlineKeyboardButton("🔙 Вернуться", callback_data="rate:back")
        ]
    ]
    
    text = (
        "✅ Профиль: " + profile_url + "\n\n"
        "Шаг 3️⃣ из 3️⃣\n\n"
        "👥 Выберите пол"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех коллбэков рейтинга"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    value = data[2] if len(data) > 2 else None
    
    if action == "gender":
        context.user_data['rate_gender'] = value
        await publish_rate_post(update, context)
    
    elif action == "vote":
        post_id = int(value) if value else None
        vote_value = int(data[3]) if len(data) > 3 else None
        await handle_vote(update, context, post_id, vote_value)
    
    elif action == "back":
        # Возврат на предыдущий шаг
        step = context.user_data.get('rate_step', 'photo')
        if step == 'profile':
            context.user_data['rate_step'] = 'photo'
            context.user_data['waiting_for'] = 'rate_photo'
            keyboard = [[InlineKeyboardButton("🚗 Отмена", callback_data="rate:cancel")]]
            await query.edit_message_text(
                "📸 Отправьте фотографию",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif step == 'gender':
            context.user_data['rate_step'] = 'profile'
            context.user_data['waiting_for'] = 'rate_profile'
            keyboard = [[InlineKeyboardButton("🔙 Вернуться", callback_data="rate:back")]]
            await query.edit_message_text(
                "🔗 Отправьте ссылку на профиль",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif action == "cancel":
        context.user_data.pop('rate_photo_file_id', None)
        context.user_data.pop('rate_profile', None)
        context.user_data.pop('rate_gender', None)
        context.user_data.pop('rate_step', None)
        context.user_data.pop('waiting_for', None)
        
        await query.edit_message_text("❌ Отменено")

async def publish_rate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация поста с опросом в канал"""
    photo_file_id = context.user_data.get('rate_photo_file_id')
    profile_url = context.user_data.get('rate_profile')
    gender = context.user_data.get('rate_gender')
    
    if not all([photo_file_id, profile_url, gender]):
        await update.callback_query.edit_message_text("❌ Ошибка: не хватает данных")
        return
    
    try:
        # Генерируем уникальный ID поста
        post_id = len(rating_data['posts']) + 1
        
        # Создаем кнопки опроса
        keyboard = [
            [
                InlineKeyboardButton("😭 -2", callback_data=f"rate:vote:{post_id}:-2"),
                InlineKeyboardButton("👎 -1", callback_data=f"rate:vote:{post_id}:-1"),
                InlineKeyboardButton("😐 0", callback_data=f"rate:vote:{post_id}:0"),
                InlineKeyboardButton("👍 +1", callback_data=f"rate:vote:{post_id}:1"),
                InlineKeyboardButton("🔥 +2", callback_data=f"rate:vote:{post_id}:2"),
            ]
        ]
        
        # Подпись
        caption = f"📊 Rate {profile_url}\n\n" \
                  f"👥 Gender: {gender.upper()}\n\n" \
                  f"👇 Выберите оценку"
        
        # Публикуем в канал
        msg = await context.bot.send_photo(
            chat_id=Config.TARGET_CHANNEL_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Сохраняем в памяти
        rating_data['posts'][post_id] = {
            'profile_url': profile_url,
            'gender': gender,
            'photo_file_id': photo_file_id,
            'caption': caption,
            'message_id': msg.message_id,
            'votes': {},  # {user_id: vote_value}
            'created_at': datetime.now()
        }
        
        # Инициализируем профиль если его нет
        if profile_url not in rating_data['profiles']:
            rating_data['profiles'][profile_url] = {
                'gender': gender,
                'total_score': 0,
                'vote_count': 0,
                'post_ids': []
            }
        
        rating_data['profiles'][profile_url]['post_ids'].append(post_id)
        
        logger.info(f"Published rate post {post_id} for {profile_url}")
        
        # Очищаем данные
        context.user_data.pop('rate_photo_file_id', None)
        context.user_data.pop('rate_profile', None)
        context.user_data.pop('rate_gender', None)
        context.user_data.pop('rate_step', None)
        
        await update.callback_query.edit_message_text(
            f"✅ **Пост опубликован!**\n\n"
            f"📊 Профиль: {profile_url}\n"
            f"👥 Пол: {gender.upper()}\n"
            f"🆔 Post ID: {post_id}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error publishing rate post: {e}")
        await update.callback_query.edit_message_text(f"❌ Ошибка при публикации: {e}")

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                     post_id: int, vote_value: int):
    """Обработка голоса пользователя"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"ID_{user_id}"
    
    if post_id not in rating_data['posts']:
        await update.callback_query.answer("❌ Пост не найден", show_alert=True)
        return
    
    post = rating_data['posts'][post_id]
    profile_url = post['profile_url']
    
    # Проверяем, голосовал ли уже этот пользователь
    vote_key = (user_id, post_id)
    old_vote = rating_data['user_votes'].get(vote_key)
    
    # Обновляем голос
    rating_data['user_votes'][vote_key] = vote_value
    post['votes'][user_id] = vote_value
    
    # Пересчитываем очки для профиля
    if profile_url in rating_data['profiles']:
        profile = rating_data['profiles'][profile_url]
        
        # Пересчитываем сумму голосов
        total_score = 0
        vote_count = 0
        
        for user_vote in post['votes'].values():
            total_score += user_vote
            vote_count += 1
        
        profile['total_score'] = total_score
        profile['vote_count'] = vote_count
        
        logger.info(f"User {username} voted {vote_value} for post {post_id} ({profile_url})")
    
    # Обновляем сообщение с новыми статистиками
    try:
        stats = get_post_stats(post_id)
        keyboard = [
            [
                InlineKeyboardButton(f"😭 -2 ({stats['-2']})", callback_data=f"rate:vote:{post_id}:-2"),
                InlineKeyboardButton(f"👎 -1 ({stats['-1']})", callback_data=f"rate:vote:{post_id}:-1"),
                InlineKeyboardButton(f"😐 0 ({stats['0']})", callback_data=f"rate:vote:{post_id}:0"),
                InlineKeyboardButton(f"👍 +1 ({stats['1']})", callback_data=f"rate:vote:{post_id}:1"),
                InlineKeyboardButton(f"🔥 +2 ({stats['2']})", callback_data=f"rate:vote:{post_id}:2"),
            ],
            [InlineKeyboardButton(f"📊 Score: {profile['total_score']} | Votes: {profile['vote_count']}", 
                                callback_data="rate:noop")]
        ]
        
        await context.bot.edit_message_reply_markup(
            chat_id=Config.TARGET_CHANNEL_ID,
            message_id=post['message_id'],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error updating post stats: {e}")
    
    # Ответ пользователю
    emoji_map = {-2: "😭", -1: "👎", 0: "😐", 1: "👍", 2: "🔥"}
    await update.callback_query.answer(f"{emoji_map.get(vote_value, '?')} Ваш голос учтен!", show_alert=False)

def get_post_stats(post_id: int) -> Dict[str, int]:
    """Получить статистику голосов для поста"""
    if post_id not in rating_data['posts']:
        return {'-2': 0, '-1': 0, '0': 0, '1': 0, '2': 0}
    
    post = rating_data['posts'][post_id]
    stats = {'-2': 0, '-1': 0, '0': 0, '1': 0, '2': 0}
    
    for vote in post['votes'].values():
        stats[str(vote)] += 1
    
    return stats

# ============= КОМАНДЫ СТАТИСТИКИ =============

async def toppeople_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать топ-10 профилей по очкам - /toppeople"""
    if not rating_data['profiles']:
        await update.message.reply_text("❌ Нет данных")
        return
    
    # Сортируем по очкам
    sorted_profiles = sorted(
        rating_data['profiles'].items(),
        key=lambda x: x[1]['total_score'],
        reverse=True
    )[:10]
    
    text = "🏆 **ТОП-10 ПРОФИЛЕЙ**\n\n"
    
    for i, (profile_url, data) in enumerate(sorted_profiles, 1):
        text += (
            f"{i}. **{profile_url}**\n"
            f"   ⭐️ Очки: {data['total_score']}\n"
            f"   🗳️ Голосов: {data['vote_count']}\n"
            f"   👥 Пол: {data['gender'].upper()}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("👯 Топ Boys", callback_data="rate:topboys"),
                InlineKeyboardButton("👯‍♀️ Топ Girls", callback_data="rate:topgirls")]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def topboys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ-10 среди мужчин - /topboys"""
    profiles = {url: data for url, data in rating_data['profiles'].items() if data['gender'] == 'boy'}
    
    if not profiles:
        await update.message.reply_text("❌ Нет данных")
        return
    
    sorted_profiles = sorted(profiles.items(), key=lambda x: x[1]['total_score'], reverse=True)[:10]
    
    text = "🧑‍🦱 **ТОП-10 BOYS**\n\n"
    
    for i, (profile_url, data) in enumerate(sorted_profiles, 1):
        text += f"{i}. {profile_url} — ⭐️ {data['total_score']} ({data['vote_count']} голосов)\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def topgirls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ-10 среди женщин - /topgirls"""
    profiles = {url: data for url, data in rating_data['profiles'].items() if data['gender'] == 'girl'}
    
    if not profiles:
        await update.message.reply_text("❌ Нет данных")
        return
    
    sorted_profiles = sorted(profiles.items(), key=lambda x: x[1]['total_score'], reverse=True)[:10]
    
    text = "👱‍♀️ **ТОП-10 GIRLS**\n\n"
    
    for i, (profile_url, data) in enumerate(sorted_profiles, 1):
        text += f"{i}. {profile_url} — ⭐️ {data['total_score']} ({data['vote_count']} голосов)\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def toppeoplereset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить все очки - /toppeoplereset (только для админов)"""
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только админы")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ СБРОСИТЬ", callback_data="rate:reset:confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="rate:reset:cancel")
        ]
    ]
    
    text = (
        "⚠️ **ВНИМАНИЕ: ПОЛНЫЙ СБРОС РЕЙТИНГА**\n\n"
        "Это удалит:\n"
        "❌ Все очки всех профилей\n"
        "❌ Все голоса\n"
        "❌ Всю историю\n\n"
        "Подтверждаете?"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Обработка сброса рейтинга"""
    query = update.callback_query
    
    if action == "confirm":
        # Полный сброс
        rating_data['posts'] = {}
        rating_data['profiles'] = {}
        rating_data['user_votes'] = {}
        
        logger.warning(f"Rating system reset by admin {update.effective_user.id}")
        
        await query.edit_message_text(
            "✅ **РЕЙТИНГ ПОЛНОСТЬЮ СБРОШЕН**\n\n"
            "Все очки, голоса и профили удалены"
        )
    else:
        await query.edit_message_text("❌ Отменено")
        # Добавьте эти функции в конец handlers/rating_handler.py (перед __all__)

async def handle_rate_moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle moderation callbacks for rating posts"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    post_id = int(data[2]) if len(data) > 2 and data[2].isdigit() else None
    
    if not Config.is_moderator(update.effective_user.id):
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if action == "approve":
        await approve_rating_post(update, context, post_id)
    elif action == "reject":
        await reject_rating_post(update, context, post_id)

async def approve_rating_post(update: Update, context: ContextTypes.DEFAULT_TYPE, post_id: int):
    """Approve rating post and publish it"""
    query = update.callback_query
    
    if post_id not in rating_data['posts']:
        await query.answer("❌ Пост не найден", show_alert=True)
        return
    
    post = rating_data['posts'][post_id]
    
    try:
        await query.answer("✅ Пост одобрен!")
        await query.edit_message_reply_markup(reply_markup=None)
        
        logger.info(f"Rating post {post_id} approved by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error approving rating post: {e}")
        await query.answer(f"❌ Ошибка: {e}", show_alert=True)

async def reject_rating_post(update: Update, context: ContextTypes.DEFAULT_TYPE, post_id: int):
    """Reject rating post"""
    query = update.callback_query
    
    if post_id not in rating_data['posts']:
        await query.answer("❌ Пост не найден", show_alert=True)
        return
    
    post = rating_data['posts'][post_id]
    
    try:
        await query.answer("❌ Пост отклонен")
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Удаляем пост из памяти
        if post_id in rating_data['posts']:
            del rating_data['posts'][post_id]
        
        logger.info(f"Rating post {post_id} rejected by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error rejecting rating post: {e}")
        await query.answer(f"❌ Ошибка: {e}", show_alert=True)

# ============= ОБНОВИТЕ __all__ =============
# Замените существующий __all__ на:

__all__ = [
    'rate_start_command',
    'handle_rate_photo',
    'handle_rate_profile',
    'handle_rate_callback',
    'handle_rate_moderation_callback',
    'toppeople_command',
    'topboys_command',
    'topgirls_command',
    'toppeoplereset_command',
    'publish_rate_post',
    'approve_rating_post',
    'reject_rating_post',
    'rating_data'
]
