"""
Telegram bot initialization module for Ovulo.
This module sets up the Telegram bot Application and registers all handlers.
"""

import os
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)

from dotenv import load_dotenv
from utils.logger import get_logger, log_error

# Load environment variables
load_dotenv()

# Configure logger for this module
logger = get_logger(__name__)


class OvuloBot:
    """Main bot class that manages the Telegram bot application."""

    def __init__(self):
        """Initialize the bot with configuration from environment variables."""
        self.token = os.getenv('BOT_TOKEN') or os.getenv('TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("BOT_TOKEN not found in environment variables")

        # Build application with post_init and post_shutdown
        self.application = (Application.builder()
                           .token(self.token)
                           .post_init(self._post_init_callback)
                           .post_shutdown(self._post_shutdown_callback)
                           .build())

        # Initialize database connection string (will be used later)
        self.db_url = self._get_db_url()

        # Scheduler will be initialized after application starts
        self.scheduler = None

        logger.info("Bot instance initialized successfully")

    def _get_db_url(self) -> str:
        """Construct database URL from environment variables."""
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'ovulo_dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')

        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    def register_handlers(self):
        """Register all command and message handlers."""
        # Import handlers
        from handlers import start_command, start_setup_callback, help_command, status_command
        from handlers.setup import setup_command, handle_webapp_data, handle_status_callback
        from handlers.settings import settings_conversation_handler
        from handlers.history import setup_history_handlers
        from handlers.notifications import setup_notifications_handlers
        from handlers.admin import get_admin_handlers
        from handlers.gdpr import get_gdpr_handlers

        # Add /start command handler
        self.application.add_handler(CommandHandler("start", start_command))

        # Add /help command handler
        self.application.add_handler(CommandHandler("help", help_command))

        # Add /setup command handler for WebApp
        self.application.add_handler(CommandHandler("setup", setup_command))

        # Add /status command handler
        self.application.add_handler(CommandHandler("status", status_command))

        # Add /settings conversation handler
        self.application.add_handler(settings_conversation_handler)

        # Add /history command handlers
        setup_history_handlers(self.application)

        # Add /notifications command handlers
        setup_notifications_handlers(self.application)

        # Add admin command handlers
        for handler in get_admin_handlers():
            self.application.add_handler(handler)

        # Add GDPR command handlers
        for handler in get_gdpr_handlers():
            self.application.add_handler(handler)

        # Add handler for WebApp data
        self.application.add_handler(MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            handle_webapp_data
        ))

        # Add callback query handler for the setup button from /start
        self.application.add_handler(
            CallbackQueryHandler(start_setup_callback, pattern="^start_setup$")
        )

        # Add callback query handler for status button from setup
        self.application.add_handler(
            CallbackQueryHandler(handle_status_callback, pattern="^show_status$")
        )

        # Add error handler
        self.application.add_error_handler(self._error_handler)

        logger.info("All handlers registered successfully")

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors that occur during bot operation with detailed logging."""
        # Extract user information if available
        user_id = None
        telegram_id = None

        if isinstance(update, Update):
            if update.effective_user:
                telegram_id = update.effective_user.id
            if update.effective_message:
                # Try to get user_id from context if stored
                user_id = context.user_data.get('user_id') if context.user_data else None

        # Log the error with structured information
        log_error(
            logger=logger,
            message="Exception while handling an update",
            error=context.error,
            user_id=user_id,
            telegram_id=telegram_id,
            update_type=type(update).__name__ if update else 'Unknown'
        )

        # Try to notify the user about the error
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "Произошла ошибка при обработке вашего запроса. "
                    "Пожалуйста, попробуйте позже или обратитесь к администратору."
                )
            except Exception as e:
                log_error(
                    logger=logger,
                    message="Failed to send error message to user",
                    error=e,
                    telegram_id=telegram_id
                )

        # Notify admin about critical errors (if configured)
        from utils.logger import notify_admin_error
        if context.error and os.getenv('ADMIN_TELEGRAM_ID'):
            try:
                error_msg = f"Error in update handler: {str(context.error)}"
                if telegram_id:
                    error_msg += f"\nUser: {telegram_id}"
                await notify_admin_error(context.bot, error_msg, context.error)
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")

    async def _post_init_callback(self, application: Application) -> None:
        """Callback executed after application initialization."""
        await self._start_scheduler()

    async def _post_shutdown_callback(self, application: Application) -> None:
        """Callback executed before application shutdown."""
        await self._stop_scheduler()

    def run(self):
        """Start the bot in polling mode."""
        logger.info("Starting bot polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def initialize(self):
        """Initialize the bot application (for webhook mode)."""
        await self.application.initialize()
        logger.info("Bot application initialized")

        # Initialize and start the notification scheduler
        await self._start_scheduler()

    async def shutdown(self):
        """Shutdown the bot application gracefully."""
        # Stop the notification scheduler
        await self._stop_scheduler()

        await self.application.shutdown()
        logger.info("Bot application shut down")

    async def _start_scheduler(self):
        """Initialize and start the notification scheduler."""
        try:
            from notifications.scheduler import notification_scheduler, init_scheduler

            # Initialize the scheduler
            await init_scheduler(self.application)

            # Store scheduler in bot_data for access in handlers
            self.application.bot_data['scheduler'] = notification_scheduler
            self.scheduler = notification_scheduler

            logger.info("Notification scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start notification scheduler: {e}")
            # Scheduler is optional, so we don't fail the entire bot

    async def _stop_scheduler(self):
        """Stop the notification scheduler."""
        try:
            from notifications.scheduler import shutdown_scheduler
            await shutdown_scheduler()
            logger.info("Notification scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping notification scheduler: {e}")


def create_bot() -> OvuloBot:
    """Factory function to create and configure the bot instance."""
    bot = OvuloBot()
    bot.register_handlers()
    return bot