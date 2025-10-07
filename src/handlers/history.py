"""
Обработчик команды /history для просмотра истории циклов
"""
from utils.logger import get_logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from datetime import datetime

from database.crud import get_user, get_user_cycles
from database.session import db_session

logger = get_logger(__name__)

# Количество циклов на странице
CYCLES_PER_PAGE = 10


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history"""
    telegram_id = update.effective_user.id

    with db_session.get_session() as session:
        user = get_user(telegram_id=telegram_id, session=session)

        if not user:
            await update.message.reply_text(
                "❌ Вы еще не зарегистрированы в боте.\n"
                "Используйте /start для начала работы."
            )
            return

        # Получаем все циклы пользователя (отсортированы по дате создания, новые первые)
        cycles = get_user_cycles(session, user.id)

        if not cycles:
            await update.message.reply_text(
                "📚 *История циклов*\n\n"
                "У вас пока нет сохраненных циклов.\n"
                "Используйте /setup для настройки первого цикла.",
                parse_mode='Markdown'
            )
            return

        # Начинаем с первой страницы
        await show_history_page(update.message, cycles, 0)


async def show_history_page(message, cycles, page):
    """Показать страницу истории циклов"""
    total_cycles = len(cycles)
    total_pages = (total_cycles + CYCLES_PER_PAGE - 1) // CYCLES_PER_PAGE

    # Получаем циклы для текущей страницы
    start_idx = page * CYCLES_PER_PAGE
    end_idx = min(start_idx + CYCLES_PER_PAGE, total_cycles)
    page_cycles = cycles[start_idx:end_idx]

    # Формируем текст сообщения
    text = f"📚 *История циклов* (страница {page + 1} из {total_pages})\n\n"

    for i, cycle in enumerate(page_cycles, start=start_idx + 1):
        # Определяем статус цикла
        if cycle.is_current:
            status = "✅ Текущий"
        else:
            status = "📋 Завершен"

        # Форматируем дату
        start_date = cycle.start_date.strftime('%d.%m.%Y')

        # Рассчитываем дату окончания цикла
        end_date = cycle.start_date
        from datetime import timedelta
        end_date = (cycle.start_date + timedelta(days=cycle.cycle_length - 1)).strftime('%d.%m.%Y')

        text += (
            f"*Цикл #{i}* {status}\n"
            f"📅 Начало: {start_date}\n"
            f"📅 Конец: {end_date}\n"
            f"⏱ Длина цикла: {cycle.cycle_length} дней\n"
            f"🩸 Длина месячных: {cycle.period_length} дней\n"
            f"🕐 Создан: {cycle.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"\n"
        )

    # Создаем клавиатуру для навигации
    keyboard = []
    nav_buttons = []

    # Кнопка "Назад"
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"history_page_{page - 1}")
        )

    # Кнопка "Вперед"
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("Вперед ➡️", callback_data=f"history_page_{page + 1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка закрытия
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="history_close")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    # Отправляем или редактируем сообщение
    if hasattr(message, 'edit_text'):
        await message.edit_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для навигации по истории"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "history_close":
        await query.message.delete()
        return

    if data.startswith("history_page_"):
        page = int(data.replace("history_page_", ""))
        telegram_id = update.effective_user.id

        with db_session.get_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)
            if user:
                cycles = get_user_cycles(session, user.id)
                await show_history_page(query.message, cycles, page)


def setup_history_handlers(application):
    """Регистрация обработчиков истории"""
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CallbackQueryHandler(history_callback, pattern="^history_"))