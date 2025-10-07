"""
Handler for /status command that displays current cycle information.
Shows current phase, key dates, and cycle predictions.
"""

from utils.logger import get_logger
from datetime import date
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from database.crud import get_user, get_current_cycle
from utils.cycle_calculator import (
    calculate_cycle_dates,
    format_date_for_user,
    calculate_current_phase
)

logger = get_logger(__name__)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command - shows current cycle information.

    Displays:
    - Current cycle phase
    - Date of last period
    - Date of next period
    - Ovulation date
    - Fertile window
    - Safe periods
    - Days until next period

    Args:
        update: Telegram update object
        context: Bot context
    """
    if not update.effective_user:
        logger.error("No effective user in update")
        return

    telegram_id = update.effective_user.id
    logger.info(f"User {telegram_id} requested cycle status")

    try:
        # Get user from database
        user = get_user(telegram_id=telegram_id)

        if not user:
            await update.message.reply_text(
                "🚫 Вы еще не зарегистрированы в системе.\n"
                "Пожалуйста, используйте команду /start для начала работы."
            )
            return

        # Get current cycle
        current_cycle = get_current_cycle(user_id=user.id)

        if not current_cycle:
            await update.message.reply_text(
                "📊 У вас еще не настроен менструальный цикл.\n\n"
                "Для начала работы с ботом необходимо настроить параметры вашего цикла.\n"
                "Используйте команду /setup для быстрой настройки."
            )
            return

        # Calculate all cycle dates and current phase
        cycle_data = calculate_cycle_dates(current_cycle)
        current_phase = cycle_data['current_phase']

        # Format phase emoji
        phase_emojis = {
            'menstruation': '🔴',
            'follicular': '🟡',
            'ovulation': '💚',
            'luteal': '🟠',
            'pre_menstruation': '🟣'
        }
        phase_emoji = phase_emojis.get(current_phase['phase'], '⚪')

        # Build status message
        message_parts = [
            f"📊 <b>Статус вашего цикла</b>\n",
            f"\n{phase_emoji} <b>Текущая фаза:</b> {current_phase['description']}",
            f"📅 <b>День цикла:</b> {current_phase['day']} из {cycle_data['cycle_length']}"
        ]

        # Add fertility status
        if current_phase['is_fertile']:
            message_parts.append("\n⚠️ <b>Внимание:</b> Вы находитесь в фертильном окне!")
        elif current_phase['is_safe']:
            message_parts.append("\n✅ <b>Статус:</b> Безопасный период")

        message_parts.append("\n")

        # Key dates section
        message_parts.append("\n📆 <b>Ключевые даты:</b>")

        # Last period
        message_parts.append(
            f"\n🔴 <b>Начало последних месячных:</b>\n"
            f"   {format_date_for_user(cycle_data['start_date'])}"
        )

        # Ovulation
        today = date.today()
        if cycle_data['ovulation_date'] >= today:
            days_until_ovulation = (cycle_data['ovulation_date'] - today).days
            if days_until_ovulation == 0:
                ovulation_text = "сегодня!"
            elif days_until_ovulation == 1:
                ovulation_text = "завтра"
            else:
                ovulation_text = f"через {days_until_ovulation} дней"

            message_parts.append(
                f"\n💚 <b>Овуляция:</b>\n"
                f"   {format_date_for_user(cycle_data['ovulation_date'])} ({ovulation_text})"
            )
        else:
            message_parts.append(
                f"\n💚 <b>Овуляция была:</b>\n"
                f"   {format_date_for_user(cycle_data['ovulation_date'])}"
            )

        # Next period
        days_until_period = current_phase['days_until_period']
        if days_until_period == 0:
            period_text = "сегодня!"
        elif days_until_period == 1:
            period_text = "завтра"
        elif days_until_period < 0:
            period_text = f"задержка {abs(days_until_period)} дней"
        else:
            period_text = f"через {days_until_period} дней"

        message_parts.append(
            f"\n🔴 <b>Следующие месячные:</b>\n"
            f"   {format_date_for_user(cycle_data['next_period'])} ({period_text})"
        )

        # Fertile window
        message_parts.append("\n")
        fertile_start = cycle_data['fertile_window']['start']
        fertile_end = cycle_data['fertile_window']['end']

        if fertile_start <= today <= fertile_end:
            message_parts.append(
                f"\n🌸 <b>Фертильное окно (текущее):</b>\n"
                f"   С {format_date_for_user(fertile_start, include_weekday=False)}\n"
                f"   По {format_date_for_user(fertile_end, include_weekday=False)}"
            )
        elif fertile_start > today:
            days_until_fertile = (fertile_start - today).days
            message_parts.append(
                f"\n🌸 <b>Фертильное окно (через {days_until_fertile} дней):</b>\n"
                f"   С {format_date_for_user(fertile_start, include_weekday=False)}\n"
                f"   По {format_date_for_user(fertile_end, include_weekday=False)}"
            )
        else:
            message_parts.append(
                f"\n🌸 <b>Фертильное окно было:</b>\n"
                f"   С {format_date_for_user(fertile_start, include_weekday=False)}\n"
                f"   По {format_date_for_user(fertile_end, include_weekday=False)}"
            )

        # Safe periods
        first_safe = cycle_data['safe_periods']['first']
        second_safe = cycle_data['safe_periods']['second']

        if first_safe or second_safe:
            message_parts.append("\n")
            message_parts.append("\n🛡️ <b>Безопасные периоды:</b>")

            if first_safe:
                safe_start, safe_end = first_safe
                if safe_start <= today <= safe_end:
                    message_parts.append(
                        f"\n   ✅ <b>Текущий период:</b>\n"
                        f"   С {format_date_for_user(safe_start, include_weekday=False)}\n"
                        f"   По {format_date_for_user(safe_end, include_weekday=False)}"
                    )
                elif safe_end < today and second_safe:
                    # Show only second safe period if first is in the past
                    pass
                else:
                    message_parts.append(
                        f"\n   1️⃣ С {format_date_for_user(safe_start, include_weekday=False)}\n"
                        f"      По {format_date_for_user(safe_end, include_weekday=False)}"
                    )

            if second_safe:
                safe_start, safe_end = second_safe
                if safe_start <= today <= safe_end:
                    message_parts.append(
                        f"\n   ✅ <b>Текущий период:</b>\n"
                        f"   С {format_date_for_user(safe_start, include_weekday=False)}\n"
                        f"   По {format_date_for_user(safe_end, include_weekday=False)}"
                    )
                elif safe_start > today:
                    days_until_safe = (safe_start - today).days
                    message_parts.append(
                        f"\n   2️⃣ С {format_date_for_user(safe_start, include_weekday=False)} "
                        f"(через {days_until_safe} дней)\n"
                        f"      По {format_date_for_user(safe_end, include_weekday=False)}"
                    )

        # Add disclaimer
        message_parts.append("\n")
        message_parts.append(
            "\n⚠️ <i>Помните: календарный метод не является надежным методом контрацепции. "
            "Расчеты приблизительны и могут варьироваться.</i>"
        )

        # Add tips based on current phase
        message_parts.append("\n")
        if current_phase['phase'] == 'menstruation':
            message_parts.append(
                "\n💡 <b>Совет:</b> Больше отдыхайте, пейте теплые напитки, "
                "избегайте интенсивных физических нагрузок."
            )
        elif current_phase['phase'] == 'ovulation':
            message_parts.append(
                "\n💡 <b>Совет:</b> Это наиболее фертильный период. "
                "Идеальное время для зачатия или, наоборот, требует особой осторожности."
            )
        elif current_phase['phase'] == 'pre_menstruation':
            message_parts.append(
                "\n💡 <b>Совет:</b> Возможны симптомы ПМС. "
                "Уменьшите потребление соли и кофеина, больше расслабляйтесь."
            )

        # Join all parts and send
        message = "\n".join(message_parts)
        await update.message.reply_text(
            message,
            parse_mode='HTML'
        )

        logger.info(f"Successfully sent status to user {telegram_id}")

    except Exception as e:
        logger.error(f"Error processing /status command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при получении статуса цикла.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )


async def handle_status_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle inline status request (from callback query).
    Wrapper for status_command that handles callback queries.

    Args:
        update: Telegram update object
        context: Bot context
    """
    # Answer the callback query first to remove loading animation
    if update.callback_query:
        await update.callback_query.answer()

        # Replace update.message with update.callback_query.message
        # to make it work with callback queries
        update._effective_message = update.callback_query.message

    # Call the main status command
    await status_command(update, context)