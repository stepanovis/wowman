"""
GDPR compliance handlers for data export and deletion.
"""

import json
import io
from datetime import datetime
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler
)
from sqlalchemy.orm import Session

from utils.logger import get_logger
from database.session import db_session
from database import crud
from models.user import User
from models.cycle import Cycle
from models.notification_settings import NotificationSettings
from models.notification_log import NotificationLog

# Set up logging
logger = get_logger(__name__)

# States for conversation
CONFIRM_DELETE = 1


async def export_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Export all user data in JSON format (GDPR compliance).

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    try:
        telegram_id = update.effective_user.id
        logger.info(f"User {telegram_id} requested data export")

        # Get user from database
        user = crud.get_user(telegram_id=telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ Вы еще не зарегистрированы в боте.\n"
                "Используйте /start для начала работы.",
                parse_mode='HTML'
            )
            return

        # Collect all user data
        with db_session.get_session() as db:
            # User basic data
            user_data = {
                "export_date": datetime.utcnow().isoformat(),
                "user": {
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "timezone": user.timezone,
                    "preferred_language": user.preferred_language,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
                    "commands_count": user.commands_count
                },
                "cycles": [],
                "notification_settings": [],
                "notification_logs": []
            }

            # Get all cycles
            cycles = crud.get_user_cycles(user.id)
            for cycle in cycles:
                user_data["cycles"].append({
                    "id": cycle.id,
                    "start_date": cycle.start_date.isoformat() if cycle.start_date else None,
                    "end_date": cycle.end_date.isoformat() if cycle.end_date else None,
                    "cycle_length": cycle.cycle_length,
                    "period_length": cycle.period_length,
                    "is_current": cycle.is_current,
                    "notes": cycle.notes,
                    "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
                    "updated_at": cycle.updated_at.isoformat() if cycle.updated_at else None
                })

            # Get notification settings
            notification_settings = crud.get_user_notification_settings(user.id)
            for setting in notification_settings:
                user_data["notification_settings"].append({
                    "id": setting.id,
                    "notification_type": setting.notification_type,
                    "is_enabled": setting.is_enabled,
                    "time_offset": setting.time_offset,
                    "created_at": setting.created_at.isoformat() if setting.created_at else None,
                    "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
                })

            # Get notification logs (last 100)
            notification_logs = crud.get_user_notification_logs(user.id, limit=100)
            for log in notification_logs:
                user_data["notification_logs"].append({
                    "id": log.id,
                    "notification_type": log.notification_type,
                    "status": log.status,
                    "error_message": log.error_message,
                    "sent_at": log.sent_at.isoformat() if log.sent_at else None
                })

        # Create JSON file
        json_data = json.dumps(user_data, ensure_ascii=False, indent=2)
        json_file = io.BytesIO(json_data.encode('utf-8'))
        json_file.name = f"ovulo_data_{telegram_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Send file to user
        await update.message.reply_document(
            document=json_file,
            filename=json_file.name,
            caption=(
                "📦 <b>Ваши данные экспортированы</b>\n\n"
                "Файл содержит все ваши данные, хранящиеся в боте:\n"
                "• Профиль пользователя\n"
                "• История циклов\n"
                "• Настройки уведомлений\n"
                "• Журнал уведомлений\n\n"
                "<i>Этот файл предоставлен в соответствии с GDPR.</i>"
            ),
            parse_mode='HTML'
        )

        logger.info(f"Data export completed for user {telegram_id}")

    except Exception as e:
        logger.error(f"Error in export_data_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при экспорте данных. Попробуйте позже.",
            parse_mode='HTML'
        )


async def delete_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the data deletion process with confirmation (GDPR compliance).

    Args:
        update: Telegram update object
        context: Telegram context object

    Returns:
        int: Next conversation state
    """
    try:
        telegram_id = update.effective_user.id
        logger.warning(f"User {telegram_id} initiated data deletion")

        # Get user from database
        user = crud.get_user(telegram_id=telegram_id)
        if not user:
            await update.message.reply_text(
                "❌ Вы еще не зарегистрированы в боте.\n"
                "Нет данных для удаления.",
                parse_mode='HTML'
            )
            return ConversationHandler.END

        # Store user_id in context for later use
        context.user_data['delete_user_id'] = user.id
        context.user_data['delete_telegram_id'] = telegram_id

        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("❌ Да, удалить все", callback_data="confirm_delete"),
                InlineKeyboardButton("✅ Отмена", callback_data="cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send confirmation message
        await update.message.reply_text(
            "⚠️ <b>ВНИМАНИЕ: Удаление данных</b>\n\n"
            "Вы запросили полное удаление всех ваших данных из бота.\n\n"
            "Это действие приведет к удалению:\n"
            "• Вашего профиля\n"
            "• Всей истории циклов\n"
            "• Настроек уведомлений\n"
            "• Журналов и статистики\n\n"
            "<b>Это действие НЕОБРАТИМО!</b>\n\n"
            "Вы уверены, что хотите удалить все данные?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        return CONFIRM_DELETE

    except Exception as e:
        logger.error(f"Error in delete_data_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            parse_mode='HTML'
        )
        return ConversationHandler.END


async def confirm_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle confirmation of data deletion.

    Args:
        update: Telegram update object
        context: Telegram context object

    Returns:
        int: End conversation state
    """
    query = update.callback_query
    await query.answer()

    try:
        if query.data == "confirm_delete":
            telegram_id = context.user_data.get('delete_telegram_id')

            if not telegram_id:
                await query.edit_message_text(
                    "❌ Ошибка: не найден идентификатор пользователя.",
                    parse_mode='HTML'
                )
                return ConversationHandler.END

            # Perform deletion
            logger.warning(f"Deleting all data for user {telegram_id}")

            # Delete user and all related data (cascade delete)
            success = crud.delete_user(telegram_id=telegram_id)

            if success:
                await query.edit_message_text(
                    "✅ <b>Данные удалены</b>\n\n"
                    "Все ваши данные были полностью удалены из бота.\n\n"
                    "Если вы захотите использовать бот снова, "
                    "вы можете начать с команды /start.\n\n"
                    "Спасибо за использование Ovulo!",
                    parse_mode='HTML'
                )
                logger.info(f"Successfully deleted all data for user {telegram_id}")
            else:
                await query.edit_message_text(
                    "❌ Произошла ошибка при удалении данных.\n"
                    "Пожалуйста, обратитесь к администратору.",
                    parse_mode='HTML'
                )
                logger.error(f"Failed to delete data for user {telegram_id}")

        else:  # cancel_delete
            await query.edit_message_text(
                "✅ <b>Удаление отменено</b>\n\n"
                "Ваши данные остаются в безопасности.\n"
                "Вы можете продолжить использование бота.",
                parse_mode='HTML'
            )
            logger.info(f"User {context.user_data.get('delete_telegram_id')} cancelled data deletion")

        # Clear context data
        context.user_data.pop('delete_user_id', None)
        context.user_data.pop('delete_telegram_id', None)

    except Exception as e:
        logger.error(f"Error in confirm_delete_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Произошла ошибка при обработке запроса.",
            parse_mode='HTML'
        )

    return ConversationHandler.END


async def cancel_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the deletion process.

    Args:
        update: Telegram update object
        context: Telegram context object

    Returns:
        int: End conversation state
    """
    await update.message.reply_text(
        "✅ Удаление данных отменено.",
        parse_mode='HTML'
    )

    # Clear context data
    context.user_data.pop('delete_user_id', None)
    context.user_data.pop('delete_telegram_id', None)

    return ConversationHandler.END


def get_gdpr_handlers():
    """
    Get GDPR-related handlers.

    Returns:
        list: List of handlers for GDPR commands
    """
    # Create conversation handler for delete_data with confirmation
    delete_conversation = ConversationHandler(
        entry_points=[CommandHandler("delete_data", delete_data_command)],
        states={
            CONFIRM_DELETE: [
                CallbackQueryHandler(confirm_delete_callback,
                                   pattern="^(confirm_delete|cancel_delete)$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_delete_command)],
    )

    return [
        CommandHandler("export_data", export_data_command),
        delete_conversation,
    ]