"""
Handler for /start command.
Handles new user registration and welcome messages.
"""

from utils.logger import get_logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.crud import get_or_create_user

# Set up logging
logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    Checks if user exists in DB, creates new user if not, and sends appropriate welcome message.

    Args:
        update: The update object from Telegram
        context: The context object from telegram.ext
    """
    if not update.effective_user:
        logger.warning("Received /start command without effective_user")
        return

    user_telegram_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name or "пользователь"

    try:
        # Get or create user in database
        db_user = get_or_create_user(
            telegram_id=user_telegram_id,
            username=username
        )

        if not db_user:
            logger.error(f"Failed to create/get user with telegram_id={user_telegram_id}")
            await update.message.reply_text(
                "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
            )
            return

        # Check if this is a new user (commands_count would be 1 for new users)
        is_new_user = db_user.commands_count <= 1

        # Create inline keyboard with "Start Setup" button
        keyboard = [
            [InlineKeyboardButton("🎯 Начать настройку", callback_data="start_setup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_new_user:
            # Welcome message for new users
            welcome_text = (
                f"Привет, {first_name}! 👋\n\n"
                "Добро пожаловать в бот для отслеживания менструального цикла!\n\n"
                "Я помогу вам:\n"
                "• 📅 Отслеживать ваш цикл\n"
                "• 🎯 Рассчитывать овуляцию и фертильное окно\n"
                "• 🔔 Напоминать о важных датах\n"
                "• 📊 Вести историю циклов\n\n"
                "Для начала работы мне нужно узнать параметры вашего цикла.\n"
                "Нажмите кнопку ниже, чтобы начать настройку."
            )

            logger.info(f"New user registered: telegram_id={user_telegram_id}, username={username}")
        else:
            # Welcome message for existing users
            welcome_text = (
                f"С возвращением, {first_name}! 👋\n\n"
                "Рад видеть вас снова!\n\n"
                "Что вы хотите сделать?\n"
                "• Используйте /status для просмотра текущего состояния цикла\n"
                "• Используйте /settings для изменения параметров\n"
                "• Используйте /history для просмотра истории циклов\n"
                "• Используйте /notifications для управления уведомлениями\n"
                "• Используйте /help для получения справки\n\n"
                "Или нажмите кнопку ниже, чтобы настроить новый цикл."
            )

            logger.info(f"Existing user returned: telegram_id={user_telegram_id}, username={username}")

        # Send the welcome message with inline keyboard
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже."
        )


async def start_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the callback from "Start Setup" button.
    Opens the WebApp for cycle setup.

    Args:
        update: The update object from Telegram
        context: The context object from telegram.ext
    """
    from handlers.setup import setup_command

    query = update.callback_query
    await query.answer()

    # Delete the original message
    await query.delete_message()

    # Create a fake update object for setup_command
    # We need to trigger setup_command which expects update.message
    logger.info(f"User {update.effective_user.id} clicked start_setup button")

    # Send setup message directly by calling the setup logic
    user = update.effective_user

    # Import here to avoid circular imports
    from database.crud import get_user, get_current_cycle
    from database.session import db_session
    import os
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    # Check if user exists in database
    with db_session.get_session() as session:
        db_user = get_user(telegram_id=user.id, session=session)
        if not db_user:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Пожалуйста, сначала используйте команду /start для регистрации."
            )
            return

    # Get WebApp URL from environment
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

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )