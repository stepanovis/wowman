"""
Handler for /setup command and WebApp data processing.
Uses Telegram WebApp for user-friendly onboarding form.
"""

import json
from utils.logger import get_logger
import os
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from database.crud import (
    get_user, create_cycle, get_current_cycle, update_cycle_status,
    create_notification_settings, get_user_notification_settings
)
from database.session import db_session
from notifications.types import NotificationType
from notifications.scheduler_utils import get_all_notification_times

logger = get_logger(__name__)


async def create_notification_tasks(user, cycle, context):
    """
    Create notification tasks for a user's cycle.

    Args:
        user: User database object
        cycle: Cycle database object
        context: Bot context containing application instance
    """
    try:
        # Get the scheduler from the bot application
        scheduler = context.bot_data.get('scheduler')
        if not scheduler:
            logger.warning("Scheduler not found in bot_data, skipping notification setup")
            return

        with db_session.get_session() as session:
            # Get or create notification settings for all types
            notification_settings = []

            # Get existing settings for the user
            existing_settings = get_user_notification_settings(
                user_id=user.id,
                session=session
            )

            # Create a dictionary for quick lookup
            existing_dict = {
                s.notification_type: s for s in existing_settings
            } if existing_settings else {}

            for notification_type in NotificationType:
                # Check if setting already exists
                existing_setting = existing_dict.get(notification_type.value)

                # Create setting if doesn't exist
                if not existing_setting:
                    setting = create_notification_settings(
                        user_id=user.id,
                        notification_type=notification_type.value,
                        is_enabled=True,
                        time_offset=0,  # Will use default time for each type
                        session=session
                    )
                    notification_settings.append(setting)
                else:
                    notification_settings.append(existing_setting)

            # Calculate notification times for all enabled notifications
            notification_times = get_all_notification_times(
                cycle=cycle,
                user=user,
                notification_settings=notification_settings
            )

            # Remove old tasks for this user
            removed_count = await scheduler.remove_user_jobs(user.id)
            if removed_count > 0:
                logger.info(f"Removed {removed_count} old notification tasks for user {user.id}")

            # Add new tasks to scheduler
            added_count = 0
            for notification_type, send_time in notification_times.items():
                job_id = await scheduler.add_notification_job(
                    user_id=user.id,
                    notification_type=notification_type,
                    send_at=send_time
                )
                if job_id:
                    added_count += 1
                    logger.info(
                        f"Scheduled {notification_type.value} notification for user {user.id} "
                        f"at {send_time}"
                    )

            logger.info(f"Created {added_count} notification tasks for user {user.id}")

    except Exception as e:
        logger.error(f"Error creating notification tasks for user {user.id}: {e}")
        # Don't raise the error - notification setup failure shouldn't break cycle creation


async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /setup command - send WebApp button for cycle configuration.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Check if user exists in database
    with db_session.get_session() as session:
        db_user = get_user(telegram_id=user.id, session=session)
        if not db_user:
            await update.message.reply_text(
                "Пожалуйста, сначала используйте команду /start для регистрации."
            )
            return

    # Create WebApp button
    # Get WebApp URL from environment or use default
    # For production, set WEBAPP_URL environment variable to your HTTPS URL
    # For development with Telegram, use ngrok: ngrok http 8080
    webapp_url = os.getenv('WEBAPP_URL', 'https://your-domain.com/webapp/setup_form.html')

    if webapp_url == 'https://your-domain.com/webapp/setup_form.html':
        logger.warning("Using default WebApp URL. Set WEBAPP_URL environment variable for production.")

    keyboard = [[
        InlineKeyboardButton(
            text="🌸 Настроить параметры цикла",
            web_app=WebAppInfo(url=webapp_url)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Check if user already has a cycle configured
    with db_session.get_session() as session:
        db_user = get_user(telegram_id=user.id, session=session)
        if db_user:
            current_cycle = get_current_cycle(user_id=db_user.id, session=session)
            if current_cycle:
                message = (
                    "У вас уже настроен текущий цикл:\n"
                    f"📅 Начало: {current_cycle.start_date.strftime('%d.%m.%Y')}\n"
                    f"🔄 Длина цикла: {current_cycle.cycle_length} дней\n"
                    f"🩸 Длина месячных: {current_cycle.period_length} дней\n\n"
                    "Нажмите кнопку ниже, чтобы обновить параметры:"
                )
            else:
                message = (
                    "Добро пожаловать в настройку цикла! 🌸\n\n"
                    "Для расчета овуляции и фертильного окна мне нужна информация о вашем цикле.\n\n"
                    "Нажмите кнопку ниже, чтобы открыть форму настройки:"
                )
        else:
            message = "Ошибка: пользователь не найден. Используйте /start для регистрации."

    await update.message.reply_text(
        message,
        reply_markup=reply_markup
    )


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle data received from WebApp form.

    Args:
        update: Telegram update object with web_app_data
        context: Bot context
    """
    user = update.effective_user

    # Extract and parse WebApp data
    try:
        web_app_data = update.message.web_app_data.data
        data = json.loads(web_app_data)

        # Validate received data
        last_period_date = datetime.strptime(data['last_period_date'], '%Y-%m-%d').date()
        cycle_length = int(data['cycle_length'])
        period_length = int(data['period_length'])

        # Additional validation
        if last_period_date > date.today():
            raise ValueError("Дата не может быть в будущем")

        if not (21 <= cycle_length <= 40):
            raise ValueError("Длина цикла должна быть от 21 до 40 дней")

        if not (1 <= period_length <= 10):
            raise ValueError("Длина месячных должна быть от 1 до 10 дней")

        # Check if date is not too old (more than 60 days)
        days_diff = (date.today() - last_period_date).days
        if days_diff > 60:
            raise ValueError("Дата слишком давняя (более 60 дней)")

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Error parsing WebApp data: {e}")
        await update.message.reply_text(
            "❌ Ошибка при обработке данных формы. Пожалуйста, попробуйте еще раз."
        )
        return

    # Save cycle to database
    try:
        with db_session.get_session() as session:
            # Get user from database
            db_user = get_user(telegram_id=user.id, session=session)
            if not db_user:
                await update.message.reply_text(
                    "Ошибка: пользователь не найден. Используйте /start для регистрации."
                )
                return

            # Deactivate current cycle if exists
            current_cycle = get_current_cycle(user_id=db_user.id, session=session)
            if current_cycle:
                update_cycle_status(session, current_cycle.id, is_current=False)
                logger.info(f"Deactivated previous cycle {current_cycle.id} for user {user.id}")

            # Create new cycle
            new_cycle = create_cycle(
                session=session,
                user_id=db_user.id,
                start_date=last_period_date,
                cycle_length=cycle_length,
                period_length=period_length,
                is_current=True
            )

            logger.info(f"Created new cycle {new_cycle.id} for user {user.id}")

            # Calculate key dates for confirmation message
            # Овуляция происходит примерно за 14 дней до конца цикла
            ovulation_date = last_period_date + timedelta(days=cycle_length - 14)

            # Следующие месячные начнутся через cycle_length дней
            next_period_date = last_period_date + timedelta(days=cycle_length)

            # Фертильное окно: 5 дней до овуляции и 1 день после
            fertile_start = ovulation_date - timedelta(days=5)
            fertile_end = ovulation_date + timedelta(days=1)

            # Send confirmation message with summary
            confirmation = (
                "✅ Параметры цикла успешно сохранены!\n\n"
                f"📅 Начало последних месячных: {last_period_date.strftime('%d.%m.%Y')}\n"
                f"🔄 Длина цикла: {cycle_length} дней\n"
                f"🩸 Длина месячных: {period_length} дней\n\n"
                f"📊 Прогноз:\n"
                f"🥚 Примерная дата овуляции: {ovulation_date.strftime('%d.%m.%Y')}\n"
                f"🌱 Фертильное окно: {fertile_start.strftime('%d.%m')} - {fertile_end.strftime('%d.%m')}\n"
                f"📅 Следующие месячные: {next_period_date.strftime('%d.%m.%Y')}\n\n"
                "Используйте /status для просмотра подробного прогноза."
            )

            # Create inline keyboard with status button
            keyboard = [[
                InlineKeyboardButton(text="📊 Посмотреть статус", callback_data="show_status")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                confirmation,
                reply_markup=reply_markup
            )

            # Create notification tasks
            await create_notification_tasks(db_user, new_cycle, context)

    except Exception as e:
        logger.error(f"Error saving cycle for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже."
        )


async def handle_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback for showing status (from inline button).

    Args:
        update: Telegram update object
        context: Bot context
    """
    from handlers.status import status_command

    query = update.callback_query
    await query.answer()

    # Set effective message for status_command to work with callback queries
    update._effective_message = query.message

    # Call the status command handler
    await status_command(update, context)


def setup_handlers(app):
    """
    Register setup-related handlers with the application.

    Args:
        app: Telegram Application instance
    """
    # Command handler for /setup
    app.add_handler(CommandHandler("setup", setup_command))

    # Handler for WebApp data
    app.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA,
        handle_webapp_data
    ))

    # Callback handler for status button
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(
        handle_status_callback,
        pattern="^show_status$"
    ))

    logger.info("Setup handlers registered")