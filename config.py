# ============= config.py - ДОБАВИТЬ В STATS_CHANNELS =============

STATS_CHANNELS = {
    'gambling_chat': int(os.getenv("GAMBLING_CHAT_ID", "-1002922212434")),
    'catalog': int(os.getenv("CATALOG_ID", "-1002601716810")),
    'trade': int(os.getenv("TRADE_ID", "-1003033694255")),
    'budapest_main': int(os.getenv("BUDAPEST_MAIN_ID", "-1002743668534")),
    'budapest_chat': int(os.getenv("BUDAPEST_CHAT_STATS_ID", "-1002883770818")),
    'partners': int(os.getenv("PARTNERS_ID", "-1002919380244")),
    'budapest_people': int(os.getenv("BUDAPEST_PEOPLE_ID", "-1003114019170")),  # НОВОЕ
}

# ============= ДОБАВИТЬ В .env =============
BUDAPEST_PEOPLE_ID=-1003114019170


# ============= handlers/rating_handler.py - ОБНОВЛЕННАЯ ВЕРСИЯ =============

async def rate_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс публикации фото с опросом - /ratestart
    ИСПРАВЛЕНО: с кулдауном 1 час и модерацией"""
    
    user_id = update.effective_user.id
    
    if not Config.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только админы могут создавать опросы")
        return
    
    # ✅ ИСПРАВЛЕНО: Проверка кулдауна 1 час для /ratestart
    from services.cooldown import cooldown_service
    
    rate_cooldown_key = f"rate_start_{user_id}"
    
    # Используем cooldown сервис
    can_use, remaining = await cooldown_service.can_post(user_id)
    
    # Дополнительная проверка кулдауна для /ratestart (1 час)
    if rate_cooldown_key in context.user_data:
        last_use = context.user_data[rate_cooldown_key]
        elapsed = (datetime.now() - last_use).total_seconds()
        
        if elapsed < 3600:  # 1 час = 3600 секунд
            remaining_minutes = int((3600 - elapsed) / 60)
            await update.message.reply_text(
                f"⏰ Вы сможете создать новый рейтинг через {remaining_minutes} минут"
            )
            return
    
    # Сохраняем время использования
    context.user_data[rate_cooldown_key] = datetime.now()
    
    context.user_data['rate_step'] = 'photo'
    context.user_data['rate_status'] = 'pending'  # Статус на модерацию
    
    keyboard = [[InlineKeyboardButton("🚗 Отмена", callback_data="rate:cancel")]]
    
    text = (
        "📊 **СОЗДАНИЕ РЕЙТИНГА С ОПРОСОМ**\n\n"
        "Шаг 1️⃣ из 3️⃣\n\n"
        "⚠️ **Новое:** Посты будут отправлены на модерацию!\n"
        "Администратор подтвердит публикацию.\n\n"
        "📸 Отправьте фотографию"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    context.user_data['waiting_for'] = 'rate_photo'


async def publish_rate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация поста с опросом - ИСПРАВЛЕНО: теперь отправляется в модерацию"""
    photo_file_id = context.user_data.get('rate_photo_file_id')
    profile_url = context.user_data.get('rate_profile')
    gender = context.user_data.get('rate_gender')
    
    if not all([photo_file_id, profile_url, gender]):
        await update.callback_query.edit_message_text("❌ Ошибка: не хватает данных")
        return
    
    try:
        # Генерируем уникальный ID поста
        post_id = len(rating_data['posts']) + 1
        
        # Создаем кнопки опроса (для финального отображения)
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
        
        # Сохраняем в памяти (ПОКА БЕЗ ПУБЛИКАЦИИ)
        rating_data['posts'][post_id] = {
            'profile_url': profile_url,
            'gender': gender,
            'photo_file_id': photo_file_id,
            'caption': caption,
            'votes': {},
            'keyboard': keyboard,
            'created_at': datetime.now(),
            'status': 'pending',  # НОВОЕ: статус модерации
            'created_by': update.effective_user.id
        }
        
        # Инициализируем профиль если его нет
        if profile_url not in rating_data['profiles']:
            rating_data['profiles'][profile_url] = {
                'gender': gender,
                'total_score': 0,
                'vote_count': 0,
                'post_ids': []
            }
        
        logger.info(f"Created rate post {post_id} for {profile_url} (pending moderation)")
        
        # ✅ НОВОЕ: Отправляем в МОДЕРАЦИЮ вместо публикации
        await send_rating_to_moderation(update, context, post_id, photo_file_id, caption, keyboard)
        
        # Очищаем данные
        context.user_data.pop('rate_photo_file_id', None)
        context.user_data.pop('rate_profile', None)
        context.user_data.pop('rate_gender', None)
        context.user_data.pop('rate_step', None)
        
        await update.callback_query.edit_message_text(
            f"✅ **Рейтинг отправлен на модерацию!**\n\n"
            f"📊 Профиль: {profile_url}\n"
            f"👥 Пол: {gender.upper()}\n"
            f"🆔 Post ID: {post_id}\n\n"
            f"⏳ Ожидайте подтверждения администратора",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error publishing rate post: {e}")
        await update.callback_query.edit_message_text(f"❌ Ошибка при создании: {e}")


async def send_rating_to_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   post_id: int, photo_file_id: str, caption: str, keyboard_data: list):
    """✅ НОВОЕ: Отправить рейтинг пост в модерацию"""
    
    bot = context.bot
    admin_username = update.effective_user.username or f"ID_{update.effective_user.id}"
    
    try:
        # Проверяем доступность группы модерации
        try:
            await bot.get_chat(Config.MODERATION_GROUP_ID)
        except Exception as e:
            logger.error(f"Cannot access moderation group: {e}")
            await bot.send_message(
                chat_id=update.effective_user.id,
                text="⚠️ Группа модерации недоступна. Обратитесь к администратору."
            )
            return
        
        # Отправляем фото
        mod_text = (
            f"⭐️ НОВЫЙ РЕЙТИНГ ДЛЯ ПУБЛИКАЦИИ\n\n"
            f"👤 От: @{admin_username}\n"
            f"🆔 Post ID: {post_id}\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📊 {caption}\n\n"
            f"⚠️ **ДЕЙСТВИЯ:**"
        )
        
        # Кнопки для модератора
        mod_keyboard = [
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data=f"rate_mod:approve:{post_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"rate_mod:reject:{post_id}")
            ]
        ]
        
        # Отправляем фото с текстом
        msg = await bot.send_photo(
            chat_id=Config.MODERATION_GROUP_ID,
            photo=photo_file_id,
            caption=mod_text,
            reply_markup=InlineKeyboardMarkup(mod_keyboard),
            parse_mode='Markdown'
        )
        
        # Сохраняем ID сообщения модерации
        rating_data['posts'][post_id]['moderation_message_id'] = msg.message_id
        
        logger.info(f"Rating post {post_id} sent to moderation (message {msg.message_id})")
        
    except Exception as e:
        logger.error(f"Error sending rating to moderation: {e}", exc_info=True)


async def handle_rate_moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ НОВОЕ: Обработка модерации рейтинг постов"""
    
    query = update.callback_query
    
    if not Config.is_moderator(query.from_user.id):
        await query.answer("❌ Нет прав", show_alert=True)
        return
    
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    post_id = int(data[2]) if len(data) > 2 and data[2].isdigit() else None
    
    if not post_id or post_id not in rating_data['posts']:
        await query.answer("❌ Пост не найден", show_alert=True)
        return
    
    post = rating_data['posts'][post_id]
    
    if action == "approve":
        await approve_rating_post(update, context, post_id, post, query)
    
    elif action == "reject":
        await reject_rating_post(update, context, post_id, post, query)


async def approve_rating_post(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              post_id: int, post: dict, query):
    """✅ НОВОЕ: Одобрить и опубликовать рейтинг пост"""
    
    try:
        bot = context.bot
        
        # Публикуем в Budapest People канал
        msg = await bot.send_photo(
            chat_id=Config.STATS_CHANNELS['budapest_people'],  # Budapest People
            photo=post['photo_file_id'],
            caption=post['caption'],
            reply_markup=InlineKeyboardMarkup(post['keyboard'])
        )
        
        # Обновляем пост
        post['status'] = 'published'
        post['message_id'] = msg.message_id
        post['published_at'] = datetime.now()
        
        logger.info(f"Rating post {post_id} approved and published")
        
        # Обновляем сообщение модерации
        try:
            await bot.edit_message_caption(
                chat_id=Config.MODERATION_GROUP_ID,
                message_id=post['moderation_message_id'],
                caption=f"✅ **ОДОБРЕНО И ОПУБЛИКОВАНО**\n\n"
                        f"📊 {post['caption']}\n"
                        f"✅ Опубликовано в: Budapest People\n"
                        f"🆔 Post ID: {post_id}",
                parse_mode='Markdown',
                reply_markup=None  # Удаляем кнопки
            )
        except Exception as e:
            logger.warning(f"Could not update moderation message: {e}")
        
        await query.answer("✅ Опубликовано!", show_alert=False)
        
        # Уведомляем автора
        try:
            await bot.send_message(
                chat_id=post['created_by'],
                text=f"✅ **Ваш рейтинг опубликован!**\n\n"
                     f"📊 Профиль: {post['profile_url']}\n"
                     f"👥 Пол: {post['gender'].upper()}\n"
                     f"📍 Канал: Budapest People\n\n"
                     f"🍀 Удачи!"
            )
        except Exception as e:
            logger.warning(f"Could not notify author: {e}")
        
    except Exception as e:
        logger.error(f"Error approving rating post: {e}")
        await query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def reject_rating_post(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             post_id: int, post: dict, query):
    """✅ НОВОЕ: Отклонить рейтинг пост"""
    
    bot = context.bot
    
    # Обновляем пост
    post['status'] = 'rejected'
    post['rejected_at'] = datetime.now()
    post['rejected_by'] = query.from_user.id
    
    # Удаляем с модерации
    try:
        await bot.delete_message(
            chat_id=Config.MODERATION_GROUP_ID,
            message_id=post['moderation_message_id']
        )
    except Exception as e:
        logger.warning(f"Could not delete moderation message: {e}")
    
    # Уведомляем автора
    try:
        await bot.send_message(
            chat_id=post['created_by'],
            text=f"❌ **Ваш рейтинг отклонен**\n\n"
                 f"📊 Профиль: {post['profile_url']}\n"
                 f"👥 Пол: {post['gender'].upper()}\n"
                 f"🆔 Post ID: {post_id}\n\n"
                 f"💡 Свяжитесь с администрацией для подробности"
        )
    except Exception as e:
        logger.warning(f"Could not notify author about rejection: {e}")
    
    logger.info(f"Rating post {post_id} rejected by {query.from_user.id}")
    
    await query.answer("❌ Отклонено", show_alert=False)


# ============= ОБНОВИТЬ main.py - ДОБавить новый обработчик =============

