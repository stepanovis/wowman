"""
Модуль для отправки уведомлений пользователям.

Реализует отправку уведомлений с обработкой ошибок и rate limiting.
"""

import asyncio
from datetime import datetime
from typing import Optional

from telegram import Bot
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)

from database.crud import (
    create_notification_log,
    get_user,
    update_user_active_status,
)
from database.session import get_db
from notifications.types import NotificationType, get_notification_message
from utils.logger import get_logger, log_error, log_notification_event

logger = get_logger(__name__)


async def send_notification_async(
    user_id: int,
    notification_type: NotificationType,
    bot_application=None
):
    """
    Асинхронная отправка уведомления пользователю.

    Используется APScheduler для вызова этой функции.

    Args:
        user_id: ID пользователя в БД
        notification_type: Тип уведомления
        bot_application: Экземпляр Application из python-telegram-bot
    """
    if bot_application:
        await send_notification(
            user_id=user_id,
            notification_type=notification_type,
            bot=bot_application.bot
        )
    else:
        logger.error(
            f"Не удалось отправить уведомление user_id={user_id}: "
            "bot_application не передан"
        )


async def send_notification(
    user_id: int,
    notification_type: NotificationType,
    bot: Bot,
    retry_count: int = 0,
    max_retries: int = 3
) -> bool:
    """
    Отправляет уведомление пользователю с обработкой ошибок и rate limiting.

    Args:
        user_id: ID пользователя в БД
        notification_type: Тип уведомления
        bot: Экземпляр бота для отправки сообщений
        retry_count: Текущее количество попыток
        max_retries: Максимальное количество попыток при rate limiting

    Returns:
        bool: True если уведомление успешно отправлено, False в противном случае
    """
    # Получаем данные пользователя из БД
    db = next(get_db())
    try:
        user = get_user(db, user_id)
        if not user:
            logger.error(f"Пользователь с ID {user_id} не найден в БД")
            return False

        if not user.is_active:
            logger.info(
                f"Пропускаем уведомление для неактивного пользователя {user_id}"
            )
            return False

        # Получаем текст уведомления
        notification_text = get_notification_message(notification_type)

        try:
            # Отправляем сообщение
            await bot.send_message(
                chat_id=user.telegram_id,
                text=notification_text,
                parse_mode="HTML"
            )

            # Записываем успешную отправку в лог
            create_notification_log(
                db=db,
                user_id=user_id,
                notification_type=notification_type.value,
                status="sent"
            )

            log_notification_event(
                logger=logger,
                event_type="sent",
                user_id=user_id,
                telegram_id=user.telegram_id,
                notification_type=notification_type.value,
                status="success"
            )
            return True

        except RetryAfter as e:
            # Обработка rate limiting
            retry_after = e.retry_after
            logger.warning(
                f"Rate limiting для user_id={user_id}: "
                f"повтор через {retry_after} секунд"
            )

            if retry_count < max_retries:
                # Ждём указанное время и повторяем попытку
                await asyncio.sleep(retry_after)
                return await send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    bot=bot,
                    retry_count=retry_count + 1,
                    max_retries=max_retries
                )
            else:
                logger.error(
                    f"Превышено количество попыток отправки для user_id={user_id}"
                )
                create_notification_log(
                    db=db,
                    user_id=user_id,
                    notification_type=notification_type.value,
                    status="failed_rate_limit"
                )
                return False

        except Forbidden as e:
            # Пользователь заблокировал бота
            logger.warning(
                f"Пользователь {user_id} заблокировал бота: {e}"
            )

            # Помечаем пользователя как неактивного
            update_user_active_status(db, user_id, is_active=False)

            create_notification_log(
                db=db,
                user_id=user_id,
                notification_type=notification_type.value,
                status="blocked"
            )
            return False

        except BadRequest as e:
            # Неверный chat_id или другие ошибки в запросе
            logger.error(
                f"Ошибка при отправке уведомления user_id={user_id}: {e}"
            )
            create_notification_log(
                db=db,
                user_id=user_id,
                notification_type=notification_type.value,
                status="failed_bad_request"
            )
            return False

        except (NetworkError, TimedOut) as e:
            # Сетевые ошибки - можно повторить попытку
            logger.warning(
                f"Сетевая ошибка при отправке уведомления user_id={user_id}: {e}"
            )

            if retry_count < max_retries:
                # Ждём немного и повторяем попытку
                await asyncio.sleep(5 * (retry_count + 1))  # Экспоненциальная задержка
                return await send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    bot=bot,
                    retry_count=retry_count + 1,
                    max_retries=max_retries
                )
            else:
                logger.error(
                    f"Превышено количество попыток для user_id={user_id} "
                    f"из-за сетевых ошибок"
                )
                create_notification_log(
                    db=db,
                    user_id=user_id,
                    notification_type=notification_type.value,
                    status="failed_network"
                )
                return False

        except TelegramError as e:
            # Любые другие ошибки Telegram
            logger.error(
                f"Telegram ошибка при отправке уведомления user_id={user_id}: {e}"
            )
            create_notification_log(
                db=db,
                user_id=user_id,
                notification_type=notification_type.value,
                status="failed_telegram_error"
            )
            return False

    except Exception as e:
        logger.exception(
            f"Неожиданная ошибка при отправке уведомления user_id={user_id}: {e}"
        )
        try:
            create_notification_log(
                db=db,
                user_id=user_id,
                notification_type=notification_type.value,
                status="failed_unexpected"
            )
        except:
            pass
        return False
    finally:
        db.close()


def send_notification_sync(
    user_id: int,
    notification_type: NotificationType,
    bot: Bot
) -> bool:
    """
    Синхронная обёртка для отправки уведомления.

    Используется для тестирования и вызова из синхронного кода.

    Args:
        user_id: ID пользователя в БД
        notification_type: Тип уведомления
        bot: Экземпляр бота для отправки сообщений

    Returns:
        bool: True если уведомление успешно отправлено
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            send_notification(
                user_id=user_id,
                notification_type=notification_type,
                bot=bot
            )
        )
        return result
    finally:
        loop.close()


async def send_test_notification(
    telegram_id: int,
    notification_type: NotificationType,
    bot: Bot
) -> bool:
    """
    Отправляет тестовое уведомление по telegram_id (для отладки).

    Args:
        telegram_id: Telegram ID пользователя
        notification_type: Тип уведомления
        bot: Экземпляр бота

    Returns:
        bool: True если успешно отправлено
    """
    try:
        notification_text = get_notification_message(notification_type)

        # Добавляем пометку что это тестовое уведомление
        test_text = (
            "⚠️ <b>ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>\n\n"
            + notification_text
        )

        await bot.send_message(
            chat_id=telegram_id,
            text=test_text,
            parse_mode="HTML"
        )

        logger.info(
            f"Тестовое уведомление {notification_type.value} отправлено "
            f"на telegram_id={telegram_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Ошибка отправки тестового уведомления: {e}"
        )
        return False