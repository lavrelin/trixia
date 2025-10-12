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

# Замените функции в handlers/rating_handler.py на эти:

async def publish_rate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить пост с опросом на модерацию (НЕ публиковать сразу!)"""
    photo_file_id = context.user_data.get('rate_photo_file_id')
    profile_url = context.user_data.get('rate_profile')
    gender = context.user_data.get('rate_gender')
    
    if not all([photo_file_id, profile_url, gender]):
        await update.callback_query.edit_message_text("❌ Ошибка: не хватает данных")
        return
    
    try:
        # Генерируем уникальный ID поста
        post_id = len(rating_data['posts']) + 1
        
        # Сохраняем в памяти для отслеживания
        rating_data['posts'][post_id] = {
            'profile_url': profile_url,
            'gender': gender,
            'photo_file_id': photo_file_id,
            'created_at': datetime.now(),
            'votes': {},
            'status': 'pending'  # Ожидает модерации
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
        
        logger.info(f"Rating post {post_id} created for {profile_url}, sending to moderation")
        
        # Отправляем на МОДЕРАЦИЮ
        await send_rating_to_moderation(update, context, post_id, photo_file_id, profile_url, gender)
        
        # Очищаем данные
        context.user_data.pop('rate_photo_file_id', None)
        context.user_data.pop('rate_profile', None)
        context.user_data.pop('rate_gender', None)
        context.user_data.pop('rate_step', None)
        
        await update.callback_query.edit_message_text(
            f"✅ **Пост отправлен на модерацию!**\n\n"
            f"📊 Профиль: {profile_url}\n"
            f"👥 Пол: {gender.upper()}\n"
            f"🆔 Post ID: {post_id}\n\n"
            f"⏳ Ожидайте публикации после проверки модератором",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error preparing rate post: {e}")
        await update.callback_query.edit_message_text(f"❌ Ошибка при подготовке: {e}")

async def send_rating_to_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     post_id: int, photo_file_id: str, 
                                     profile_url: str, gender: str):
    """Отправить пост на модерацию"""
    bot = context.bot
    
    try:
        # Создаем кнопки для модератора
        keyboard = [
            [
                InlineKeyboardButton("✅ Опубликовать в Budapest People", callback_data=f"rate_mod:approve:{post_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"rate_mod:reject:{post_id}")
            ]
        ]
        
        # Отправляем фото с описанием в группу модерации
        caption = (
            f"📊 **НОВЫЙ ПОСТ НА МОДЕРАЦИЮ (Rating)**\n\n"
            f"👤 Профиль: {profile_url}\n"
            f"👥 Пол: {gender.upper()}\n"
            f"🆔 Post ID: {post_id}\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👇 Выберите действие:"
        )
        
        msg = await bot.send_photo(
            chat_id=Config.MODERATION_GROUP_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Сохраняем ID сообщения модерации
        rating_data['posts'][post_id]['moderation_message_id'] = msg.message_id
        rating_data['posts'][post_id]['moderation_group_id'] = Config.MODERATION_GROUP_ID
        
        logger.info(f"Rating post {post_id} sent to moderation group {Config.MODERATION_GROUP_ID}")
        
    except Exception as e:
        logger.error(f"Error sending rating post to moderation: {e}")
        raise

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
    """Одобрить и ОПУБЛИКОВАТЬ пост в Budapest People (-1003114019170)"""
    query = update.callback_query
    
    if post_id not in rating_data['posts']:
        await query.answer("❌ Пост не найден", show_alert=True)
        return
    
    post = rating_data['posts'][post_id]
    profile_url = post['profile_url']
    gender = post['gender']
    photo_file_id = post['photo_file_id']
    
    try:
        # 🎯 ПУБЛИКУЕМ В BUDAPEST PEOPLE (-1003114019170)
        BUDAPEST_PEOPLE_ID = -1003114019170
        
        keyboard = [
            [
                InlineKeyboardButton("😭 -2 (0)", callback_data=f"rate:vote:{post_id}:-2"),
                InlineKeyboardButton("👎 -1 (0)", callback_data=f"rate:vote:{post_id}:-1"),
                InlineKeyboardButton("😐 0 (0)", callback_data=f"rate:vote:{post_id}:0"),
                InlineKeyboardButton("👍 +1 (0)", callback_data=f"rate:vote:{post_id}:1"),
                InlineKeyboardButton("🔥 +2 (0)", callback_data=f"rate:vote:{post_id}:2"),
            ],
            [InlineKeyboardButton(f"📊 Score: 0 | Votes: 0", callback_data="rate:noop")]
        ]
        
        caption = f"📊 Rate {profile_url}\n\n👥 Gender: {gender.upper()}\n\n👇 Выберите оценку"
        
        # 🎯 ОТПРАВЛЯЕМ В BUDAPEST PEOPLE
        msg = await context.bot.send_photo(
            chat_id=BUDAPEST_PEOPLE_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Обновляем данные поста
        post['message_id'] = msg.message_id
        post['published_channel_id'] = BUDAPEST_PEOPLE_ID
        post['status'] = 'published'
        
        # Удаляем кнопки из сообщения модератора
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Обновляем текст модератора
        new_caption = (
            f"{query.message.caption}\n\n"
            f"✅ **ОДОБРЕНО И ОПУБЛИКОВАНО**\n"
            f"📍 Канал: Budapest People\n"
            f"🔗 https://t.me/c/1003114019170/{msg.message_id}"
        )
        
        await query.edit_message_caption(
            caption=new_caption,
            parse_mode='Markdown'
        )
        
        await query.answer("✅ Пост опубликован в Budapest People!", show_alert=False)
        logger.info(f"Rating post {post_id} approved and published to Budapest People ({BUDAPEST_PEOPLE_ID})")
        
    except Exception as e:
        logger.error(f"Error approving rating post: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {e}", show_alert=True)

async def reject_rating_post(update: Update, context: ContextTypes.DEFAULT_TYPE, post_id: int):
    """Отклонить пост"""
    query = update.callback_query
    
    if post_id not in rating_data['posts']:
        await query.answer("❌ Пост не найден", show_alert=True)
        return
    
    try:
        # Удаляем пост из памяти
        if post_id in rating_data['posts']:
            del rating_data['posts'][post_id]
        
        # Обновляем сообщение модератора
        await query.edit_message_reply_markup(reply_markup=None)
        
        new_caption = (
            f"{query.message.caption}\n\n"
            f"❌ **ОТКЛОНЕНО**"
        )
        
        await query.edit_message_caption(
            caption=new_caption,
            parse_mode='Markdown'
        )
        
        await query.answer("❌ Пост отклонен и удален", show_alert=False)
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
