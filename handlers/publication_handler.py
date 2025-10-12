# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from config import Config
from services.db import db
from services.cooldown import CooldownService
from services.hashtags import HashtagService
from services.filter_service import FilterService
from models import User, Post, PostStatus
from sqlalchemy import select
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def handle_publication_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle publication callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None
    
    if action == "cat":
        # Subcategory selected
        subcategory = data[2] if len(data) > 2 else None
        await start_post_creation(update, context, subcategory)
    elif action == "preview":
        await show_preview(update, context)
    elif action == "send":
        await send_to_moderation(update, context)
    elif action == "edit":
        await edit_post(update, context)
    elif action == "cancel":
        await cancel_post_with_reason(update, context)
    elif action == "cancel_confirm":
        await cancel_post(update, context)
    elif action == "add_media":
        await request_media(update, context)
    elif action == "back":
        # ÐÐ¾Ð·Ð²ÑÐ°Ñ Ðº Ð¿ÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑÑ
        await show_preview(update, context)

async def start_post_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, subcategory: str):
    """Start creating a post with selected subcategory"""
    subcategory_names = {
        'work': 'ð· Ð Ð°Ð±Ð¾ÑÐ°',
        'rent': 'ðï¸ ÐÑÐµÐ½Ð´Ð°',
        'buy': 'ðµð»ââï¸ ÐÑÐ¿Ð»Ñ',
        'sell': 'ðµð½ ÐÑÐ¾Ð´Ð°Ð¼',
        'events': 'ð Ð¡Ð¾Ð±ÑÑÐ¸Ñ',
        'free': 'ðµð¼ ÐÑÐ´Ð°Ð¼ Ð´Ð°ÑÐ¾Ð¼',
        'important': 'âï¸ÑÐµ ÐÑÐ´Ð°Ð¿ÐµÑÑ',
        'other': 'â ÐÑÑÐ³Ð¾Ðµ'
    }
    
    # Ð¡Ð¾ÑÑÐ°Ð½ÑÐµÐ¼ Ð´Ð°Ð½Ð½ÑÐµ Ð¿Ð¾ÑÑÐ°
    context.user_data['post_data'] = {
        'category': 'ð¯ï¸ ÐÑÐ´Ð°Ð¿ÐµÑÑ',
        'subcategory': subcategory_names.get(subcategory, 'â ÐÑÑÐ³Ð¾Ðµ'),
        'anonymous': False
    }

    keyboard = [[InlineKeyboardButton("â®ï¸ ÐÐµÑÐ½ÑÑÑÑÑ", callback_data="menu:announcements")]]
    
    await update.callback_query.edit_message_text(
        f"ð¯ï¸ ÐÑÐ´Ð°Ð¿ÐµÑÑ â â¼ï¸ ÐÐ±ÑÑÐ²Ð»ÐµÐ½Ð¸Ñ â {subcategory_names.get(subcategory)}\n\n"
        "ð¥ ÐÐ°Ð¿Ð¸ÑÐ¸ÑÐµ ÑÐµÐºÑÑ, Ð´Ð¾Ð±Ð°Ð²ÑÑÐµ ÑÐ¾ÑÐ¾, Ð²Ð¸Ð´ÐµÐ¾ ÐºÐ¾Ð½ÑÐµÐ½Ñ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    context.user_data['waiting_for'] = 'post_text'

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ÐÐ±ÑÐ°Ð±Ð¾ÑÐºÐ° ÑÐµÐºÑÑÐ° Ð¾Ñ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ñ"""
    
    # ÐÑÐ¾Ð²ÐµÑÑÐµÐ¼, ÐµÑÑÑ Ð»Ð¸ Ð¼ÐµÐ´Ð¸Ð° Ð²Ð¼ÐµÑÑÐµ Ñ ÑÐµÐºÑÑÐ¾Ð¼
    has_media = update.message.photo or update.message.video or update.message.document
    
    # ÐÑÐ»Ð¸ Ð¼ÐµÐ´Ð¸Ð° Ð¸ ÑÐµÐºÑÑ Ð¾Ð´Ð½Ð¾Ð²ÑÐµÐ¼ÐµÐ½Ð½Ð¾ (caption)
    if has_media and update.message.caption:
        text = update.message.caption
        
        # ÐÑÐ»Ð¸ Ð¶Ð´ÑÐ¼ ÑÐµÐºÑÑ Ð¿Ð¾ÑÑÐ°
        if context.user_data.get('waiting_for') == 'post_text':
            # ÐÑÐ¾Ð²ÐµÑÑÐµÐ¼ Ð½Ð° Ð·Ð°Ð¿ÑÐµÑÑÐ½Ð½ÑÐµ ÑÑÑÐ»ÐºÐ¸
            filter_service = FilterService()
            if filter_service.contains_banned_link(text) and not Config.is_moderator(update.effective_user.id):
                await handle_link_violation(update, context)
                return
            
            # Ð¡Ð¾ÑÑÐ°Ð½ÑÐµÐ¼ ÑÐµÐºÑÑ
            if 'post_data' not in context.user_data:
                context.user_data['post_data'] = {}
            
            context.user_data['post_data']['text'] = text
            context.user_data['post_data']['media'] = []
            
            # Ð¡Ð¾ÑÑÐ°Ð½ÑÐµÐ¼ Ð¼ÐµÐ´Ð¸Ð°
            if update.message.photo:
                context.user_data['post_data']['media'].append({
                    'type': 'photo',
                    'file_id': update.message.photo[-1].file_id
                })
            elif update.message.video:
                context.user_data['post_data']['media'].append({
                    'type': 'video',
                    'file_id': update.message.video.file_id
                })
            elif update.message.document:
                context.user_data['post_data']['media'].append({
                    'type': 'document',
                    'file_id': update.message.document.file_id
                })
            
            keyboard = [
                [
                    InlineKeyboardButton("ð¸ ÐÑÐµ Ð¼ÐµÐ´Ð¸Ð°?", callback_data="pub:add_media"),
                    InlineKeyboardButton("ð» ÐÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑ", callback_data="pub:preview")
                ],
                [InlineKeyboardButton("ð ÐÐµÑÐ½ÑÑÑÑÑ", callback_data="menu:back")]
            ]
            
            await update.message.reply_text(
                "â ÐÑÐ»Ð¸ÑÐ½Ð¾, ÑÐµÐºÑÑ Ð¸ Ð¼ÐµÐ´Ð¸Ð° ÑÐ¾ÑÑÐ°Ð½ÐµÐ½Ñ!\n\n"
                "ð ÐÑ Ð¼Ð¾Ð¶ÐµÑÐµ Ð´Ð¾Ð±Ð°Ð²Ð¸ÑÑ ÐµÑÐµ Ð¼ÐµÐ´Ð¸Ð° Ð¸Ð»Ð¸ Ð¿ÐµÑÐµÐ¹ÑÐ¸ Ðº Ð¿ÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑÑ?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['waiting_for'] = None
            return
    
    # ÐÑÐ»Ð¸ ÑÐ¾Ð»ÑÐºÐ¾ ÑÐµÐºÑÑ Ð±ÐµÐ· Ð¼ÐµÐ´Ð¸Ð°
    if 'waiting_for' not in context.user_data:
        return
    
    waiting_for = context.user_data['waiting_for']
    text = update.message.text if update.message.text else update.message.caption
    
    if not text:
        return
    
    logger.info(f"Text input received. waiting_for: {waiting_for}")
    
    if waiting_for == 'post_text':
        # Check for links
        filter_service = FilterService()
        if filter_service.contains_banned_link(text) and not Config.is_moderator(update.effective_user.id):
            await handle_link_violation(update, context)
            return
        
        if 'post_data' not in context.user_data:
            await update.message.reply_text(
                "ð¤ Ð£Ð¿Ñ! ÐÐ°Ð½Ð½ÑÐµ Ð¿Ð¾ÑÑÐ° Ð¿Ð¾ÑÐµÑÑÐ»Ð¸ÑÑ.\n"
                "ÐÐ°Ð²Ð°Ð¹ÑÐµ Ð½Ð°ÑÐ½ÐµÐ¼ Ð·Ð°Ð½Ð¾Ð²Ð¾ Ñ /start"
            )
            context.user_data.pop('waiting_for', None)
            return
        
        context.user_data['post_data']['text'] = text
        context.user_data['post_data']['media'] = []
        
        keyboard = [
            [
                InlineKeyboardButton("ð¹ ÐÑÐ¸ÐºÑÐµÐ¿Ð¸ÑÑ Ð¼ÐµÐ´Ð¸Ð° ÐºÐ¾Ð½ÑÐµÐ½Ñ", callback_data="pub:add_media"),
                InlineKeyboardButton("ð ÐÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑ", callback_data="pub:preview")
            ],
            [InlineKeyboardButton("ð¶ââï¸ ÐÐ°Ð·Ð°Ð´", callback_data="menu:back")]
        ]
        
        await update.message.reply_text(
            "ð ÐÑÐ»Ð¸ÑÐ½ÑÐ¹ ÑÐµÐºÑÑ, ÑÐ¾ÑÑÐ°Ð½ÑÑ!\n\n"
            "ð ÐÐ¾Ð±Ð°Ð²Ð¸ÑÑ ÐµÑÑ ÑÐ¾ÑÐ¾, Ð²Ð¸Ð´ÐµÐ¾ Ð¸Ð»Ð¸ ÑÐ¼Ð¾ÑÑÐ¸Ð¼ ÑÑÐ¾ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['waiting_for'] = None
        
    elif waiting_for == 'cancel_reason':
        context.user_data['cancel_reason'] = text
        await cancel_post(update, context)
        
    elif waiting_for.startswith('piar_'):
        from handlers.piar_handler import handle_piar_text
        field = waiting_for.replace('piar_', '')
        await handle_piar_text(update, context, field, text)

async def handle_media_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media input from user"""
    # ÐÑÐ¾Ð²ÐµÑÑÐµÐ¼, ÑÑÐ¾ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ñ Ð² Ð¿ÑÐ¾ÑÐµÑÑÐµ Ð´Ð¾Ð±Ð°Ð²Ð»ÐµÐ½Ð¸Ñ Ð¼ÐµÐ´Ð¸Ð°
    if 'post_data' not in context.user_data:
        return
    
    # ÐÑÐ¸Ð½Ð¸Ð¼Ð°ÐµÐ¼ Ð¼ÐµÐ´Ð¸Ð° Ð´Ð°Ð¶Ðµ ÐµÑÐ»Ð¸ waiting_for Ð½Ðµ ÑÑÑÐ°Ð½Ð¾Ð²Ð»ÐµÐ½
    if 'media' not in context.user_data['post_data']:
        context.user_data['post_data']['media'] = []
    
    media_added = False
    
    if update.message.photo:
        # Get highest quality photo
        context.user_data['post_data']['media'].append({
            'type': 'photo',
            'file_id': update.message.photo[-1].file_id
        })
        media_added = True
        logger.info(f"Added photo: {update.message.photo[-1].file_id}")
        
    elif update.message.video:
        context.user_data['post_data']['media'].append({
            'type': 'video',
            'file_id': update.message.video.file_id
        })
        media_added = True
        logger.info(f"Added video: {update.message.video.file_id}")
        
    elif update.message.document:
        context.user_data['post_data']['media'].append({
            'type': 'document',
            'file_id': update.message.document.file_id
        })
        media_added = True
        logger.info(f"Added document: {update.message.document.file_id}")
    
    if media_added:
        total_media = len(context.user_data['post_data']['media'])
        
        keyboard = [
            [
                InlineKeyboardButton(f"ð ÐÐ¾Ð±Ð°Ð²Ð¸ÑÑ ÐµÑÐµ", callback_data="pub:add_media"),
                InlineKeyboardButton("ð¤© ÐÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑ", callback_data="pub:preview")
            ],
            [InlineKeyboardButton("ð¶ ÐÐ°Ð·Ð°Ð´", callback_data="menu:back")]
        ]
        
        await update.message.reply_text(
            f"â ÐÐµÐ´Ð¸Ð° Ð¿Ð¾Ð»ÑÑÐµÐ½Ð¾! (ÐÑÐµÐ³Ð¾: {total_media})\n\n"
            "ð ÐÐ¾Ð±Ð°Ð²Ð¸ÑÑ ÐµÑÐµ Ð¸Ð»Ð¸ ÑÐ¼Ð¾ÑÑÐµÑÑ ÑÐµÐ·ÑÐ»ÑÑÐ°Ñ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['waiting_for'] = None

async def request_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request media from user"""
    context.user_data['waiting_for'] = 'post_media'
    
    keyboard = [[InlineKeyboardButton("ð ÐÐ°Ð·Ð°Ð´", callback_data="pub:preview")]]
    
    await update.callback_query.edit_message_text(
        "ð¹ ÐÐ¾Ð´ÐµÐ»Ð¸ÑÐµÑÑ ÑÐ¾ÑÐ¾, Ð²Ð¸Ð´ÐµÐ¾ Ð¸Ð»Ð¸ Ð´Ð¾ÐºÑÐ¼ÐµÐ½ÑÐ¾Ð¼:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show post preview with media first, then buttons"""
    if 'post_data' not in context.user_data:
        await update.callback_query.edit_message_text("ðµ ÐÑÐ¸Ð±ÐºÐ°: Ð´Ð°Ð½Ð½ÑÐµ Ð¿Ð¾ÑÑÐ° Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ñ")
        return
    
    post_data = context.user_data['post_data']
    
    # Generate hashtags
    hashtag_service = HashtagService()
    
    # Ð¡Ð¿ÐµÑÐ¸Ð°Ð»ÑÐ½ÑÐµ ÑÐµÑÑÐµÐ³Ð¸ Ð´Ð»Ñ ÐÐºÑÑÐ°Ð»ÑÐ½Ð¾Ð³Ð¾
    if post_data.get('is_actual'):
        hashtags = ['#ÐÐºÑÑÐ°Ð»ÑÐ½Ð¾Ðµâ¡ï¸', '@Trixlivebot']
    else:
        hashtags = hashtag_service.generate_hashtags(
            post_data.get('category'),
            post_data.get('subcategory')
        )
    
    # Build preview text
    preview_text = f"{post_data.get('text', '')}\n\n"
    preview_text += f"{' '.join(hashtags)}\n\n"
    preview_text += Config.DEFAULT_SIGNATURE
    
    keyboard = [
        [
            InlineKeyboardButton("ð¨ ÐÑÐ¿ÑÐ°Ð²Ð¸ÑÑ Ð½Ð° Ð¼Ð¾Ð´ÐµÑÐ°ÑÐ¸Ñ", callback_data="pub:send"),
            InlineKeyboardButton("ð ÐÐ·Ð¼ÐµÐ½Ð¸ÑÑ", callback_data="pub:edit")
        ],
        [InlineKeyboardButton("ð ÐÑÐ¼ÐµÐ½Ð°", callback_data="pub:cancel")]
    ]
    
    # ÐÐ¡ÐÐ ÐÐÐÐÐÐ: Ð¡Ð½Ð°ÑÐ°Ð»Ð° ÑÐ´Ð°Ð»ÑÐµÐ¼ ÑÑÐ°ÑÐ¾Ðµ ÑÐ¾Ð¾Ð±ÑÐµÐ½Ð¸Ðµ Ñ ÐºÐ½Ð¾Ð¿ÐºÐ°Ð¼Ð¸
    try:
        if update.callback_query:
            await update.callback_query.delete_message()
    except:
        pass
    
    # ÐÐ¡ÐÐ ÐÐÐÐÐÐ: Ð¡Ð½Ð°ÑÐ°Ð»Ð° Ð¿Ð¾ÐºÐ°Ð·ÑÐ²Ð°ÐµÐ¼ Ð¼ÐµÐ´Ð¸Ð°, ÐµÑÐ»Ð¸ ÐµÑÑÑ
    media = post_data.get('media', [])
    if media:
        try:
            for i, media_item in enumerate(media[:5]):  # ÐÐ¾ÐºÐ°Ð·ÑÐ²Ð°ÐµÐ¼ Ð´Ð¾ 5 Ð¼ÐµÐ´Ð¸Ð° ÑÐ°Ð¹Ð»Ð¾Ð²
                caption = None
                if i == 0:  # ÐÐµÑÐ²Ð¾Ðµ Ð¼ÐµÐ´Ð¸Ð° Ñ Ð¿Ð¾Ð´Ð¿Ð¸ÑÑÑ
                    caption = f"ð¿ ÐÐµÐ´Ð¸Ð° ÑÐ°Ð¹Ð»Ñ ({len(media)} ÑÑ.)"
                
                if media_item.get('type') == 'photo':
                    await update.effective_message.reply_photo(
                        photo=media_item['file_id'],
                        caption=caption
                    )
                elif media_item.get('type') == 'video':
                    await update.effective_message.reply_video(
                        video=media_item['file_id'],
                        caption=caption
                    )
                elif media_item.get('type') == 'document':
                    await update.effective_message.reply_document(
                        document=media_item['file_id'],
                        caption=caption
                    )
        except Exception as e:
            logger.error(f"Error showing media preview: {e}")
    
    # ÐÐ¡ÐÐ ÐÐÐÐÐÐ: ÐÐ¾ÑÐ¾Ð¼ Ð¿Ð¾ÐºÐ°Ð·ÑÐ²Ð°ÐµÐ¼ ÑÐµÐºÑÑ Ñ ÐºÐ½Ð¾Ð¿ÐºÐ°Ð¼Ð¸ (Ð¿Ð¾ÑÐ»ÐµÐ´Ð½ÐµÐµ ÑÐ¾Ð¾Ð±ÑÐµÐ½Ð¸Ðµ)
    try:
        await update.effective_message.reply_text(
            f"ð«£ *ÐÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑ Ð¿Ð¾ÑÑÐ°:*\n\n{preview_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending preview text: {e}")
        # Fallback Ð±ÐµÐ· ÑÐ¾ÑÐ¼Ð°ÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð¸Ñ
        await update.effective_message.reply_text(
            f"ÐÑÐµÐ´Ð¿ÑÐ¾ÑÐ¼Ð¾ÑÑ Ð¿Ð¾ÑÑÐ°:\n\n{preview_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ÐÐ°Ð¼ÐµÐ½Ð¸ ÑÑÐ¸ ÑÑÐ½ÐºÑÐ¸Ð¸ Ð² handlers/publication_handler.py

async def send_to_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send post to moderation with fixed cooldown check"""
    user_id = update.effective_user.id
    post_data = context.user_data.get('post_data')
    
    if not post_data:
        await update.callback_query.edit_message_text("ð¥ ÐÐ°Ð½Ð½ÑÐµ Ð¿Ð¾ÑÑÐ° Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ñ")
        return
    
    try:
        # ÐÐ¡ÐÐ ÐÐÐÐÐÐÐ: Ð¿ÑÐ¾Ð²ÐµÑÑÐµÐ¼ Ð´Ð¾ÑÑÑÐ¿Ð½Ð¾ÑÑÑ ÐÐ
        if not db.session_maker:
            logger.error("Database not available")
            await update.callback_query.edit_message_text(
                "ð ÐÐ°Ð·Ð° Ð´Ð°Ð½Ð½ÑÑ Ð½ÐµÐ´Ð¾ÑÑÑÐ¿Ð½Ð°. ÐÐ¾Ð¿ÑÐ¾Ð±ÑÐ¹ÑÐµ Ð¿Ð¾Ð·Ð¶Ðµ Ð¸Ð»Ð¸ Ð¾Ð±ÑÐ°ÑÐ¸ÑÐµÑÑ Ðº Ð°Ð´Ð¼Ð¸Ð½Ð¸ÑÑÑÐ°ÑÐ¾ÑÑ."
            )
            return
        
        async with db.get_session() as session:
            # Get user
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found in database")
                await update.callback_query.edit_message_text(
                    "ð© ÐÐ¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ñ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½. ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐ¹ÑÐµ /start Ð´Ð»Ñ ÑÐµÐ³Ð¸ÑÑÑÐ°ÑÐ¸Ð¸."
                )
                return
            
            # ÐÐ¡ÐÐ ÐÐÐÐÐÐÐ: Ð¿ÑÐ¾Ð²ÐµÑÑÐµÐ¼ ÐºÑÐ»Ð´Ð°ÑÐ½ Ð¿ÑÐ°Ð²Ð¸Ð»ÑÐ½Ð¾
            from services.cooldown import cooldown_service
            
            try:
                can_post, remaining_seconds = await cooldown_service.can_post(user_id)
            except Exception as cooldown_error:
                logger.warning(f"Cooldown check failed: {cooldown_error}")
                can_post = cooldown_service.simple_can_post(user_id)
                remaining_seconds = cooldown_service.get_remaining_time(user_id)
            
            if not can_post and not Config.is_moderator(user_id):
                remaining_minutes = remaining_seconds // 60
                await update.callback_query.edit_message_text(
                    f"ð¤ ÐÑÐ¶Ð½Ð¾ Ð¿Ð¾Ð´Ð¾Ð¶Ð´Ð°ÑÑ ÐµÑÐµ {remaining_minutes} Ð¼Ð¸Ð½ÑÑ Ð´Ð¾ ÑÐ»ÐµÐ´ÑÑÑÐµÐ³Ð¾ Ð¿Ð¾ÑÑÐ°"
                )
                return
            
            # ÐÐ¡ÐÐ ÐÐÐÐÐÐ: ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐµÐ¼ PostStatus.PENDING Ð²Ð¼ÐµÑÑÐ¾ PostStatus.PENDING
            from models import PostStatus  # ÐÑÐ°Ð²Ð¸Ð»ÑÐ½ÑÐ¹ Ð¸Ð¼Ð¿Ð¾ÑÑ
            
            create_post_data = {
                'user_id': int(user_id),
                'category': str(post_data.get('category', ''))[:255] if post_data.get('category') else None,
                'subcategory': str(post_data.get('subcategory', ''))[:255] if post_data.get('subcategory') else None,
                'text': str(post_data.get('text', ''))[:4096] if post_data.get('text') else None,
                'hashtags': list(post_data.get('hashtags', [])),
                'anonymous': bool(post_data.get('anonymous', False)),
                'media': list(post_data.get('media', [])),
                'status': PostStatus.PENDING,  # ÐÐ¡ÐÐ ÐÐÐÐÐÐ: Ð¸ÑÐ¿Ð¾Ð»ÑÐ·ÑÐµÐ¼ Ð¿ÑÐ°Ð²Ð¸Ð»ÑÐ½Ð¾Ðµ Ð·Ð½Ð°ÑÐµÐ½Ð¸Ðµ
                'is_piar': False
            }
            
            # Create post
            post = Post(**create_post_data)
            session.add(post)
            await session.flush()
            
            post_id = post.id
            logger.info(f"Created post with ID: {post_id}")
            
            await session.commit()
            
            # Refresh post
            await session.refresh(post)
            
            # Send to moderation
            await send_to_moderation_group(update, context, post, user)
            
            # Update cooldown
            try:
                await cooldown_service.update_cooldown(user_id)
            except Exception:
                cooldown_service.set_last_post_time(user_id)
            
            # Clean up
            context.user_data.pop('post_data', None)
            context.user_data.pop('waiting_for', None)
            
            await update.callback_query.edit_message_text(
                "â ÐÐ¾ÑÑ Ð¾ÑÐ¿ÑÐ°Ð²Ð»ÐµÐ½ Ð½Ð° Ð¼Ð¾Ð´ÐµÑÐ°ÑÐ¸Ñ!\n"
                "â¹ï¸ ÐÐ¶Ð¸Ð´Ð°Ð¹ÑÐµ ÑÑÑÐ»ÐºÑ Ð½Ð° ÑÐ²Ð¾Ñ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸Ñ Ð² ÐÐ¡"
            )
            
    except Exception as e:
        logger.error(f"Error sending to moderation: {e}", exc_info=True)
        await update.callback_query.edit_message_text(
            "ð ÐÑÐ¸Ð±ÐºÐ° Ð¿ÑÐ¸ Ð¾ÑÐ¿ÑÐ°Ð²ÐºÐµ Ð½Ð° Ð¼Ð¾Ð´ÐµÑÐ°ÑÐ¸Ñ"
        )


async def send_to_moderation_group(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   post: Post, user: User):
    """Send post to moderation group - ÐÐ¡ÐÐ ÐÐÐÐÐÐÐÐ¯ Ð²ÐµÑÑÐ¸Ñ"""
    bot = context.bot
    
    is_actual = context.user_data.get('post_data', {}).get('is_actual', False)
    target_group = Config.MODERATION_GROUP_ID
    
    def escape_markdown(text):
        """Ð­ÐºÑÐ°Ð½Ð¸ÑÑÐµÑ ÑÐ¿ÐµÑÐ¸Ð°Ð»ÑÐ½ÑÐµ ÑÐ¸Ð¼Ð²Ð¾Ð»Ñ markdown"""
        if not text:
            return text
        text = str(text)
        text = text.replace('*', '\\*')
        text = text.replace('_', '\\_')
        text = text.replace('[', '\\[')
        text = text.replace(']', '\\]')
        text = text.replace('`', '\\`')
        return text
    
    username = user.username or 'no_username'
    category = post.category or 'Unknown'
    
    if is_actual:
        mod_text = (
            f"â¡ï¸ ÐÐÐ¢Ð£ÐÐÐ¬ÐÐÐ - ÐÐ°ÑÐ²Ð¾ÑÐºÐ° Ð·Ð°Ð»ÐµÑÐµÐ»Ð°\n\n"
            f"ð Ð¾Ñ: @{username} (ID: {user.id})\n"
            f"ð¥ ÐÑÐ¸Ð¼ÐµÑÐ½Ð¾ Ð²: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"ð Ð Ð°Ð·Ð´ÐµÐ»: {category}\n"
            f"ð¯ ÐÑÐ´ÐµÑ Ð¾Ð¿ÑÐ±Ð»Ð¸ÐºÐ¾Ð²Ð°Ð½Ð¾ Ð² Ð§ÐÐ¢Ðµ Ð¸ ÐÐÐÐ ÐÐÐÐÐÐ"
        )
    else:
        mod_text = (
            f"ð¨ ÐÐ°ÑÐ²Ð¾ÑÐºÐ° Ð·Ð°Ð»ÐµÑÐµÐ»Ð°\n\n"
            f"ð Ð¾Ñ: @{username} (ID: {user.id})\n"
            f"ð¥ ÐÑÐ¸Ð¼ÐµÑÐ½Ð¾ Ð²: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"ð ÐÐ· ÑÐ°Ð·Ð´ÐµÐ»Ð°: {category}"
        )
    
    if post.subcategory:
        mod_text += f" â {post.subcategory}"
    
    if post.anonymous:
        mod_text += "\nð« ÐÐ½Ð¾Ð½Ð¸Ð¼Ð½Ð¾"
    
    media_count = 0
    if post.media:
        try:
            media_count = len(post.media) if isinstance(post.media, list) else 0
            if media_count > 0:
                mod_text += f"\nð ÐÐµÐ´Ð¸Ð°: {media_count} ÑÐ°Ð¹Ð»(Ð¾Ð²)"
        except (TypeError, AttributeError):
            logger.warning(f"Invalid media data for post {post.id}: {post.media}")
    
    if post.text:
        post_text = post.text[:500] + "..." if len(post.text) > 500 else post.text
        mod_text += f"\n\nð Ð¢ÐµÐºÑÑ:\n{escape_markdown(post_text)}"
    else:
        mod_text += f"\n\nð Ð¢ÐµÐºÑÑ: (Ð±ÐµÐ· ÑÐµÐºÑÑÐ°)"
    
    if post.hashtags:
        try:
            hashtags_text = " ".join(str(tag) for tag in post.hashtags)
            mod_text += f"\n\n#ï¸â£ Ð¥ÐµÑÑÐµÐ³Ð¸: {escape_markdown(hashtags_text)}"
        except (TypeError, AttributeError):
            logger.warning(f"Invalid hashtags data for post {post.id}: {post.hashtags}")
    
    if is_actual:
        keyboard = [
            [
                InlineKeyboardButton("â Ð Ð§ÐÐ¢ + ÐÐÐÐ ÐÐÐÐ¢Ð¬", callback_data=f"mod:approve_chat:{post.id}"),
                InlineKeyboardButton("â ÐÑÐºÐ»Ð¾Ð½Ð¸ÑÑ", callback_data=f"mod:reject:{post.id}")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("â ÐÐ¿ÑÐ±Ð»Ð¸ÐºÐ¾Ð²Ð°ÑÑ", callback_data=f"mod:approve:{post.id}"),
                InlineKeyboardButton("â ÐÑÐºÐ»Ð¾Ð½Ð¸ÑÑ", callback_data=f"mod:reject:{post.id}")
            ]
        ]
    
    try:
        # ÐÑÐ¾Ð²ÐµÑÑÐµÐ¼ Ð´Ð¾ÑÑÑÐ¿Ð½Ð¾ÑÑÑ Ð³ÑÑÐ¿Ð¿Ñ Ð¼Ð¾Ð´ÐµÑÐ°ÑÐ¸Ð¸
        try:
            await bot.get_chat(target_group)
        except Exception as chat_error:
            logger.error(f"Cannot access moderation group {target_group}: {chat_error}")
            await bot.send_message(
                chat_id=user.id,
                text="â ï¸ ÐÑÑÐ¿Ð¿Ð° Ð¼Ð¾Ð´ÐµÑÐ°ÑÐ¸Ð¸ Ð½ÐµÐ´Ð¾ÑÑÑÐ¿Ð½Ð°. ÐÐ±ÑÐ°ÑÐ¸ÑÐµÑÑ Ðº Ð°Ð´Ð¼Ð¸Ð½Ð¸ÑÑÑÐ°ÑÐ¾ÑÑ."
            )
            return

        # ÐÑÐ¿ÑÐ°Ð²Ð»ÑÐµÐ¼ Ð¼ÐµÐ´Ð¸Ð° ÐµÑÐ»Ð¸ ÐµÑÑÑ
        media_messages = []
        if post.media and media_count > 0:
            for i, media_item in enumerate(post.media):
                try:
                    if not media_item or not isinstance(media_item, dict):
                        logger.warning(f"Invalid media item {i}: {media_item}")
                        continue
                        
                    file_id = media_item.get('file_id')
                    media_type = media_item.get('type')
                    
                    if not file_id or not media_type:
                        logger.warning(f"Missing file_id or type in media item {i}: {media_item}")
                        continue
                    
                    caption = f"ð· ÐÐµÐ´Ð¸Ð° {i+1}/{media_count}"
                    if is_actual:
                        caption += " â¡ï¸"
                    
                    if media_type == 'photo':
                        msg = await bot.send_photo(
                            chat_id=target_group,
                            photo=file_id,
                            caption=caption
                        )
                        media_messages.append(msg.message_id)
                    elif media_type == 'video':
                        msg = await bot.send_video(
                            chat_id=target_group,
                            video=file_id,
                            caption=caption
                        )
                        media_messages.append(msg.message_id)
                    elif media_type == 'document':
                        msg = await bot.send_document(
                            chat_id=target_group,
                            document=file_id,
                            caption=caption
                        )
                        media_messages.append(msg.message_id)
                        
                except Exception as e:
                    logger.error(f"Error sending media {i+1} for post {post.id}: {e}")
                    continue
        
        # ÐÑÐ¿ÑÐ°Ð²Ð»ÑÐµÐ¼ ÑÐµÐºÑÑ Ñ ÐºÐ½Ð¾Ð¿ÐºÐ°Ð¼Ð¸
        try:
            message = await bot.send_message(
                chat_id=target_group,
                text=mod_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"â Post {post.id} sent to moderation successfully")
        except Exception as text_error:
            logger.error(f"Error sending moderation text: {text_error}")
            simple_text = (
                f"ÐÐ¾Ð²Ð°Ñ Ð·Ð°ÑÐ²ÐºÐ° Ð¾Ñ @{username} (ID: {user.id})\n"
                f"ÐÐ°ÑÐµÐ³Ð¾ÑÐ¸Ñ: {category}\n"
                f"Ð¢ÐµÐºÑÑ: {(post.text or '')[:200]}..."
            )
            message = await bot.send_message(
                chat_id=target_group,
                text=simple_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Ð¡Ð¾ÑÑÐ°Ð½ÑÐµÐ¼ message ID
        try:
            from sqlalchemy import text
            async with db.get_session() as session:
                await session.execute(
                    text("UPDATE posts SET moderation_message_id = :msg_id WHERE id = :post_id"),
                    {"msg_id": message.message_id, "post_id": int(post.id)}
                )
                await session.commit()
                logger.info(f"â Saved moderation_message_id for post {post.id}")
        except Exception as save_error:
            logger.warning(f"Could not save moderation_message_id: {save_error}")
            
    except Exception as e:
        logger.error(f"â Error sending to moderation group: {e}", exc_info=True)
        try:
            error_details = str(e)[:200] + "..." if len(str(e)) > 200 else str(e)
            await bot.send_message(
                chat_id=user.id,
                text=(
                    f"â ï¸ ÐÑÐ¸Ð±ÐºÐ° Ð¾ÑÐ¿ÑÐ°Ð²ÐºÐ¸ Ð² Ð³ÑÑÐ¿Ð¿Ñ Ð¼Ð¾Ð´ÐµÑÐ°ÑÐ¸Ð¸\n\n"
                    f"ÐÐµÑÐ°Ð»Ð¸ Ð¾ÑÐ¸Ð±ÐºÐ¸: {error_details}\n\n"
                    f"ID Ð³ÑÑÐ¿Ð¿Ñ: {target_group}\n\n"
                    f"ÐÐ±ÑÐ°ÑÐ¸ÑÐµÑÑ Ðº Ð°Ð´Ð¼Ð¸Ð½Ð¸ÑÑÑÐ°ÑÐ¾ÑÑ."
                )
            )
        except Exception as notify_error:
            logger.error(f"Could not notify user about error: {notify_error}")

async def cancel_post_with_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for cancellation reason"""
    keyboard = [
        [InlineKeyboardButton("ð¤ ÐÐµÑÐµÐ´ÑÐ¼Ð°Ð»", callback_data="pub:cancel_confirm")],
        [InlineKeyboardButton("ð ÐÑÐ¸Ð±ÐºÐ° Ð² ÑÐµÐºÑÑÐµ", callback_data="pub:cancel_confirm")],
        [InlineKeyboardButton("ðÐÐ°Ð·Ð°Ð´", callback_data="pub:preview")]
    ]
    
    await update.callback_query.edit_message_text(
        "ð­ Ð£ÐºÐ°Ð¶Ð¸ÑÐµ Ð¿ÑÐ¸ÑÐ¸Ð½Ñ Ð¾ÑÐ¼ÐµÐ½Ñ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_link_violation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle link violation"""
    await update.message.reply_text(
        "ð« ÐÐ±Ð½Ð°ÑÑÐ¶ÐµÐ½Ð° Ð·Ð°Ð¿ÑÐµÑÐµÐ½Ð½Ð°Ñ ÑÑÑÐ»ÐºÐ°!\n"
        "Ð¡ÑÑÐ»ÐºÐ¸ Ð·Ð°Ð¿ÑÐµÑÐµÐ½Ñ Ð² Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸ÑÑ."
    )
    context.user_data.pop('waiting_for', None)

async def edit_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit post before sending"""
    context.user_data['waiting_for'] = 'post_text'
    
    keyboard = [[InlineKeyboardButton("ð ÐÐ°Ð·Ð°Ð´", callback_data="pub:preview")]]
    
    await update.callback_query.edit_message_text(
        "âï¸ ÐÑÐ¿ÑÐ°Ð²ÑÑÐµ Ð½Ð¾Ð²ÑÐ¹ ÑÐµÐºÑÑ Ð¿ÑÐ±Ð»Ð¸ÐºÐ°ÑÐ¸Ð¸:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel post creation"""
    context.user_data.pop('post_data', None)
    context.user_data.pop('waiting_for', None)
    context.user_data.pop('cancel_reason', None)
    
    from handlers.start_handler import show_main_menu
    await show_main_menu(update, context)
