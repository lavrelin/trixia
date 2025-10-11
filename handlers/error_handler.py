# handlers/error_handler.py
async def global_error_handler(update, context):
    """Централизованная обработка ошибок"""
    error_msg = str(context.error)[:200]
    
    # Логируем
    logger.error(f"Error: {error_msg}", exc_info=context.error)
    
    # Уведомляем админов
    await admin_notifications.notify_error(
        error_type=type(context.error).__name__,
        error_message=error_msg,
        user_id=update.effective_user.id if update else None
    )
    
    # Отправляем пользователю нейтральное сообщение
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Команда перехвачена. "
            "Администратор уведомлен."
        )
