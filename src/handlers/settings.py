"""
Settings command handler for the Ovulo bot.
Provides interface for managing cycle parameters with inline calendar support.
"""

from utils.logger import get_logger
from datetime import datetime, date
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

from database.crud import get_user, get_current_cycle, update_cycle
from database.session import db_session
from handlers.setup import create_notification_tasks

# Configure logger
logger = get_logger(__name__)

# Conversation states
CHOOSING_ACTION = 0
UPDATING_DATE = 1
UPDATING_CYCLE_LENGTH = 2
UPDATING_PERIOD_LENGTH = 3

# Calendar settings
CALENDAR_CALLBACK = "calendar"


class CustomCalendar(DetailedTelegramCalendar):
    """Custom calendar with Russian localization and date validation."""

    # Russian month names
    MONTHS = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    # Russian day names
    DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    def __init__(self, **kwargs):
        """Initialize calendar with max date restriction."""
        super().__init__(**kwargs)
        # Set maximum date to today (cannot select future dates)
        self.max_date = date.today()


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /settings command - show settings menu.

    Args:
        update: Telegram update object
        context: Bot context

    Returns:
        Conversation state
    """
    telegram_id = update.effective_user.id

    try:
        # Get user from database
        with db_session.get_session() as session:
            user = get_user(telegram_id=telegram_id, session=session)

            if not user:
                await update.message.reply_text(
                    "⚠️ Вы еще не зарегистрированы в системе.\n"
                    "Используйте команду /start для начала работы."
                )
                return ConversationHandler.END

            # Get current cycle
            cycle = get_current_cycle(user_id=user.id, session=session)

            if not cycle:
                await update.message.reply_text(
                    "📊 У вас еще не настроен цикл.\n"
                    "Используйте команду /setup для первоначальной настройки."
                )
                return ConversationHandler.END

            # Create settings menu
            keyboard = [
                [InlineKeyboardButton("📅 Изменить дату начала цикла", callback_data="change_date")],
                [InlineKeyboardButton("🔄 Изменить длину цикла", callback_data="change_cycle_length")],
                [InlineKeyboardButton("🩸 Изменить длину месячных", callback_data="change_period_length")],
                [InlineKeyboardButton("📊 Посмотреть текущие настройки", callback_data="show_settings")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="close")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Format current settings
            settings_text = (
                "⚙️ <b>Настройки вашего цикла</b>\n\n"
                f"📅 Дата начала последних месячных: <b>{cycle.start_date.strftime('%d.%m.%Y')}</b>\n"
                f"🔄 Длина цикла: <b>{cycle.cycle_length} дней</b>\n"
                f"🩸 Длина месячных: <b>{cycle.period_length} дней</b>\n\n"
                "Выберите параметр для изменения:"
            )

            await update.message.reply_text(
                settings_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

            return CHOOSING_ACTION

    except Exception as e:
        logger.error(f"Error in settings_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при загрузке настроек.\n"
            "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def handle_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle settings menu button clicks.

    Args:
        update: Telegram update object
        context: Bot context

    Returns:
        Conversation state
    """
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id

    if query.data == "close":
        await query.message.edit_text("✅ Настройки закрыты.")
        return ConversationHandler.END

    try:
        with db_session.get_session() as session:
            user = get_user(telegram_id=telegram_id, session=session)
            cycle = get_current_cycle(user_id=user.id, session=session)

            if query.data == "show_settings":
                # Show current settings
                settings_text = (
                    "📊 <b>Ваши текущие настройки:</b>\n\n"
                    f"📅 Дата начала последних месячных: <b>{cycle.start_date.strftime('%d.%m.%Y')}</b>\n"
                    f"🔄 Длина цикла: <b>{cycle.cycle_length} дней</b>\n"
                    f"🩸 Длина месячных: <b>{cycle.period_length} дней</b>\n\n"
                    f"🕐 Дата создания записи: {cycle.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                )

                if cycle.updated_at:
                    settings_text += f"✏️ Последнее обновление: {cycle.updated_at.strftime('%d.%m.%Y %H:%M')}\n"

                # Calculate next period
                next_period = cycle.get_next_period_date()
                if next_period:
                    settings_text += f"\n📅 Следующие месячные: <b>{next_period.strftime('%d.%m.%Y')}</b>"

                # Add back button
                keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.message.edit_text(
                    settings_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return CHOOSING_ACTION

            elif query.data == "back_to_menu":
                # Return to main settings menu
                keyboard = [
                    [InlineKeyboardButton("📅 Изменить дату начала цикла", callback_data="change_date")],
                    [InlineKeyboardButton("🔄 Изменить длину цикла", callback_data="change_cycle_length")],
                    [InlineKeyboardButton("🩸 Изменить длину месячных", callback_data="change_period_length")],
                    [InlineKeyboardButton("📊 Посмотреть текущие настройки", callback_data="show_settings")],
                    [InlineKeyboardButton("❌ Закрыть", callback_data="close")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                settings_text = (
                    "⚙️ <b>Настройки вашего цикла</b>\n\n"
                    f"📅 Дата начала: <b>{cycle.start_date.strftime('%d.%m.%Y')}</b>\n"
                    f"🔄 Длина цикла: <b>{cycle.cycle_length} дней</b>\n"
                    f"🩸 Длина месячных: <b>{cycle.period_length} дней</b>\n\n"
                    "Выберите параметр для изменения:"
                )

                await query.message.edit_text(
                    settings_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return CHOOSING_ACTION

            elif query.data == "change_date":
                # Store cycle_id in context for later use
                context.user_data['cycle_id'] = cycle.id

                # Show calendar for date selection
                calendar, step = CustomCalendar(
                    current_date=cycle.start_date,
                    locale='ru'
                ).build()

                await query.message.edit_text(
                    f"📅 <b>Изменение даты начала цикла</b>\n\n"
                    f"Текущая дата: <b>{cycle.start_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"Выберите новую дату начала последних месячных ({LSTEP[step]}):",
                    reply_markup=calendar,
                    parse_mode='HTML'
                )
                return UPDATING_DATE

            elif query.data == "change_cycle_length":
                # Store cycle_id in context
                context.user_data['cycle_id'] = cycle.id

                # Add cancel button
                keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.message.edit_text(
                    f"🔄 <b>Изменение длины цикла</b>\n\n"
                    f"Текущая длина цикла: <b>{cycle.cycle_length} дней</b>\n\n"
                    "Введите новую длину цикла (от 21 до 40 дней):",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return UPDATING_CYCLE_LENGTH

            elif query.data == "change_period_length":
                # Store cycle_id in context
                context.user_data['cycle_id'] = cycle.id

                # Add cancel button
                keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.message.edit_text(
                    f"🩸 <b>Изменение длины месячных</b>\n\n"
                    f"Текущая длина месячных: <b>{cycle.period_length} дней</b>\n\n"
                    "Введите новую длину месячных (от 1 до 10 дней):",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return UPDATING_PERIOD_LENGTH

    except Exception as e:
        logger.error(f"Error in handle_settings_menu: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Произошла ошибка при обработке запроса.\n"
            "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def handle_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle calendar interactions for date selection.

    Args:
        update: Telegram update object
        context: Bot context

    Returns:
        Conversation state
    """
    query = update.callback_query

    # Process calendar callback
    result, key, step = CustomCalendar(locale='ru').process(query.data)

    if not result and key:
        # Calendar is still being navigated
        await query.message.edit_text(
            f"📅 Выберите дату начала последних месячных ({LSTEP[step]}):",
            reply_markup=key,
            parse_mode='HTML'
        )
        return UPDATING_DATE
    elif result:
        # Date selected
        selected_date = result

        # Validate that date is not in the future
        if selected_date > date.today():
            await query.answer("❌ Нельзя выбрать будущую дату!", show_alert=True)

            # Show calendar again
            calendar, step = CustomCalendar(
                current_date=date.today(),
                locale='ru'
            ).build()

            await query.message.edit_text(
                "📅 <b>Выберите дату начала последних месячных</b>\n\n"
                "⚠️ Дата не может быть в будущем!\n\n"
                f"Выберите дату ({LSTEP[step]}):",
                reply_markup=calendar,
                parse_mode='HTML'
            )
            return UPDATING_DATE

        # Update cycle in database
        cycle_id = context.user_data.get('cycle_id')
        if not cycle_id:
            await query.message.edit_text(
                "❌ Ошибка: не найден идентификатор цикла.\n"
                "Пожалуйста, начните заново с команды /settings"
            )
            return ConversationHandler.END

        try:
            updated_cycle = update_cycle(
                cycle_id=cycle_id,
                updates={'start_date': selected_date}
            )

            if updated_cycle:
                # Calculate next period
                next_period = updated_cycle.get_next_period_date()
                next_period_text = ""
                if next_period:
                    next_period_text = f"\n📅 Следующие месячные: <b>{next_period.strftime('%d.%m.%Y')}</b>"

                # Update notification tasks
                with db_session.get_session() as session:
                    user = get_user(telegram_id=update.effective_user.id, session=session)
                    if user:
                        await create_notification_tasks(user, updated_cycle, context)

                await query.message.edit_text(
                    f"✅ <b>Дата успешно обновлена!</b>\n\n"
                    f"📅 Новая дата начала цикла: <b>{selected_date.strftime('%d.%m.%Y')}</b>"
                    f"{next_period_text}\n\n"
                    "Используйте /settings для изменения других параметров\n"
                    "или /status для просмотра текущего состояния цикла.",
                    parse_mode='HTML'
                )
            else:
                await query.message.edit_text(
                    "❌ Не удалось обновить дату.\n"
                    "Пожалуйста, попробуйте позже."
                )

        except Exception as e:
            logger.error(f"Error updating cycle date: {e}", exc_info=True)
            await query.message.edit_text(
                "❌ Произошла ошибка при обновлении даты.\n"
                "Пожалуйста, попробуйте позже."
            )

        return ConversationHandler.END

    return UPDATING_DATE


async def handle_cycle_length_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle cycle length text input.

    Args:
        update: Telegram update object
        context: Bot context

    Returns:
        Conversation state
    """
    try:
        # Parse input
        cycle_length = int(update.message.text.strip())

        # Validate
        if not (21 <= cycle_length <= 40):
            await update.message.reply_text(
                "⚠️ Длина цикла должна быть от 21 до 40 дней.\n"
                "Пожалуйста, введите корректное значение:"
            )
            return UPDATING_CYCLE_LENGTH

        # Update in database
        cycle_id = context.user_data.get('cycle_id')
        if not cycle_id:
            await update.message.reply_text(
                "❌ Ошибка: не найден идентификатор цикла.\n"
                "Пожалуйста, начните заново с команды /settings"
            )
            return ConversationHandler.END

        updated_cycle = update_cycle(
            cycle_id=cycle_id,
            updates={'cycle_length': cycle_length}
        )

        if updated_cycle:
            # Calculate next period
            next_period = updated_cycle.get_next_period_date()
            next_period_text = ""
            if next_period:
                next_period_text = f"\n📅 Следующие месячные: <b>{next_period.strftime('%d.%m.%Y')}</b>"

            # Update notification tasks
            with db_session.get_session() as session:
                user = get_user(telegram_id=update.effective_user.id, session=session)
                if user:
                    await create_notification_tasks(user, updated_cycle, context)

            await update.message.reply_text(
                f"✅ <b>Длина цикла успешно обновлена!</b>\n\n"
                f"🔄 Новая длина цикла: <b>{cycle_length} дней</b>"
                f"{next_period_text}\n\n"
                "Используйте /settings для изменения других параметров\n"
                "или /status для просмотра текущего состояния цикла.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить длину цикла.\n"
                "Пожалуйста, попробуйте позже."
            )

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите число от 21 до 40:"
        )
        return UPDATING_CYCLE_LENGTH
    except Exception as e:
        logger.error(f"Error updating cycle length: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении длины цикла.\n"
            "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def handle_period_length_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle period length text input.

    Args:
        update: Telegram update object
        context: Bot context

    Returns:
        Conversation state
    """
    try:
        # Parse input
        period_length = int(update.message.text.strip())

        # Validate
        if not (1 <= period_length <= 10):
            await update.message.reply_text(
                "⚠️ Длина месячных должна быть от 1 до 10 дней.\n"
                "Пожалуйста, введите корректное значение:"
            )
            return UPDATING_PERIOD_LENGTH

        # Update in database
        cycle_id = context.user_data.get('cycle_id')
        if not cycle_id:
            await update.message.reply_text(
                "❌ Ошибка: не найден идентификатор цикла.\n"
                "Пожалуйста, начните заново с команды /settings"
            )
            return ConversationHandler.END

        updated_cycle = update_cycle(
            cycle_id=cycle_id,
            updates={'period_length': period_length}
        )

        if updated_cycle:
            # Update notification tasks
            with db_session.get_session() as session:
                user = get_user(telegram_id=update.effective_user.id, session=session)
                if user:
                    await create_notification_tasks(user, updated_cycle, context)

            await update.message.reply_text(
                f"✅ <b>Длина месячных успешно обновлена!</b>\n\n"
                f"🩸 Новая длина месячных: <b>{period_length} дней</b>\n\n"
                "Используйте /settings для изменения других параметров\n"
                "или /status для просмотра текущего состояния цикла.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить длину месячных.\n"
                "Пожалуйста, попробуйте позже."
            )

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите число от 1 до 10:"
        )
        return UPDATING_PERIOD_LENGTH
    except Exception as e:
        logger.error(f"Error updating period length: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении длины месячных.\n"
            "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the conversation.

    Args:
        update: Telegram update object
        context: Bot context

    Returns:
        Conversation state (END)
    """
    # Handle both message and callback query
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "❌ Операция отменена.\n"
            "Используйте /settings для управления настройками."
        )
    else:
        await update.message.reply_text(
            "❌ Операция отменена.\n"
            "Используйте /settings для управления настройками."
        )

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END


# Create conversation handler for settings
settings_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", settings_command)],
    states={
        CHOOSING_ACTION: [
            CallbackQueryHandler(handle_settings_menu, pattern="^(show_settings|back_to_menu|change_date|change_cycle_length|change_period_length|close)$")
        ],
        UPDATING_DATE: [
            CallbackQueryHandler(handle_calendar, pattern="^cbcal"),
            CallbackQueryHandler(cancel, pattern="^cancel$")
        ],
        UPDATING_CYCLE_LENGTH: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cycle_length_input),
            CallbackQueryHandler(cancel, pattern="^cancel$")
        ],
        UPDATING_PERIOD_LENGTH: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_period_length_input),
            CallbackQueryHandler(cancel, pattern="^cancel$")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(cancel, pattern="^close$")
    ]
)