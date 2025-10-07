"""
Centralized logging configuration for the Ovulo bot.

This module provides:
- Structured logging setup
- Log level configuration via environment variable
- Formatters for different environments
- Utility functions for logging errors
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps
import traceback


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format for better parsing
    in production environments.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            log_data['traceback'] = traceback.format_exception(*record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'telegram_id'):
            log_data['telegram_id'] = record.telegram_id
        if hasattr(record, 'notification_type'):
            log_data['notification_type'] = record.notification_type
        if hasattr(record, 'error_code'):
            log_data['error_code'] = record.error_code

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output in development mode.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format the message
        result = super().format(record)

        # Reset levelname for other handlers
        record.levelname = levelname

        return result


def setup_logging(
    log_level: Optional[str] = None,
    use_structured: Optional[bool] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_structured: Use structured JSON logging (auto-detected from environment)
        log_file: Optional log file path
    """
    # Get configuration from environment if not provided
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    if use_structured is None:
        # Use structured logging in production
        use_structured = os.getenv('ENV', 'development').lower() == 'production'

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if use_structured:
        # Production: Use structured JSON logging
        console_formatter = StructuredFormatter()
    else:
        # Development: Use colored, human-readable format
        console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        console_formatter = ColoredFormatter(console_format)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)

        # Always use structured format for file logs
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
    configure_third_party_loggers()

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={log_level}, "
        f"structured={use_structured}, "
        f"file={log_file or 'none'}"
    )


def configure_third_party_loggers():
    """Configure log levels for third-party libraries."""
    # Reduce noise from HTTP libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)

    # Reduce SQLAlchemy noise (only show warnings)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # APScheduler - show info and above
    logging.getLogger("apscheduler").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger):
    """
    Decorator to log function calls with arguments and results.

    Usage:
        @log_function_call(logger)
        def my_function(arg1, arg2):
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} returned: {result}")
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func_name}: {e}",
                    exc_info=True,
                    extra={'function': func_name}
                )
                raise

        return wrapper
    return decorator


def log_error(
    logger: logging.Logger,
    message: str,
    error: Exception,
    **extra_fields
) -> None:
    """
    Log an error with structured information.

    Args:
        logger: Logger instance
        message: Error message
        error: Exception instance
        **extra_fields: Additional fields to include in the log
    """
    logger.error(
        message,
        exc_info=error,
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            **extra_fields
        }
    )


def log_notification_event(
    logger: logging.Logger,
    event_type: str,
    user_id: int,
    telegram_id: Optional[int] = None,
    notification_type: Optional[str] = None,
    status: Optional[str] = None,
    **extra_fields
) -> None:
    """
    Log notification-related events with structured information.

    Args:
        logger: Logger instance
        event_type: Type of event (sent, failed, scheduled, etc.)
        user_id: Database user ID
        telegram_id: Telegram user ID
        notification_type: Type of notification
        status: Event status
        **extra_fields: Additional fields to include
    """
    logger.info(
        f"Notification event: {event_type}",
        extra={
            'event_type': event_type,
            'user_id': user_id,
            'telegram_id': telegram_id,
            'notification_type': notification_type,
            'status': status,
            **extra_fields
        }
    )


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    success: bool,
    duration_ms: Optional[float] = None,
    **extra_fields
) -> None:
    """
    Log database operations with performance metrics.

    Args:
        logger: Logger instance
        operation: Operation type (insert, update, delete, select)
        table: Table name
        success: Whether operation was successful
        duration_ms: Operation duration in milliseconds
        **extra_fields: Additional fields
    """
    level = logging.DEBUG if success else logging.ERROR
    logger.log(
        level,
        f"Database {operation} on {table}: {'success' if success else 'failed'}",
        extra={
            'db_operation': operation,
            'db_table': table,
            'db_success': success,
            'db_duration_ms': duration_ms,
            **extra_fields
        }
    )


def create_admin_notifier(admin_chat_id: Optional[str] = None):
    """
    Create a function to send critical errors to admin via Telegram.

    Args:
        admin_chat_id: Admin's Telegram chat ID (from environment if not provided)

    Returns:
        Function to send notifications to admin
    """
    admin_id = admin_chat_id or os.getenv('ADMIN_TELEGRAM_ID')

    if not admin_id:
        # Return a no-op function if admin ID is not configured
        return lambda *args, **kwargs: None

    async def notify_admin(bot, error_message: str, error: Optional[Exception] = None):
        """Send error notification to admin."""
        try:
            from datetime import datetime

            message = (
                f"⚠️ <b>OVULO BOT ERROR</b>\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Error: {error_message}\n"
            )

            if error:
                message += f"Exception: {type(error).__name__}: {str(error)}\n"

            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            # Log but don't raise - we don't want notification errors
            # to break the main application
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to notify admin: {e}")

    return notify_admin


# Initialize admin notifier (will be no-op if not configured)
notify_admin_error = create_admin_notifier()