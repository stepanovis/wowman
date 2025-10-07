#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функционала отправки уведомлений (TASK-026).

Проверяет:
1. Отправку уведомлений
2. Сохранение в notification_log
3. Обработку ошибок
4. Rate limiting (симуляция)
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Добавляем путь к модулям проекта
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()


async def test_notification_functions():
    """Тестирование функций отправки уведомлений."""

    from telegram import Bot
    from notifications.types import NotificationType
    from notifications.sender import (
        send_notification,
        send_test_notification,
        send_notification_sync
    )
    from database.crud import get_user_by_telegram_id, get_user_notification_logs as get_notification_logs
    from database.session import get_db

    # Получаем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN не найден в .env файле")
        return

    # Создаём экземпляр бота
    bot = Bot(token=bot_token)

    # Тестовый telegram_id (замените на свой для тестирования)
    test_telegram_id = int(os.getenv('TEST_TELEGRAM_ID', '0'))

    if test_telegram_id == 0:
        logger.error(
            "Установите TEST_TELEGRAM_ID в .env файле для тестирования "
            "(ваш Telegram ID для получения тестовых уведомлений)"
        )
        return

    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ОТПРАВКИ УВЕДОМЛЕНИЙ (TASK-026)")
    print("="*60)

    # Получаем пользователя из БД
    db = next(get_db())
    try:
        user = get_user_by_telegram_id(test_telegram_id, session=db)

        if not user:
            print(f"\n❌ Пользователь с telegram_id {test_telegram_id} не найден в БД")
            print("Сначала зарегистрируйтесь в боте через /start")
            return

        print(f"\n✅ Найден пользователь: {user.username} (ID: {user.id})")
        print(f"   Активен: {user.is_active}")
        print(f"   Часовой пояс: {user.timezone}")

        # Тест 1: Отправка тестового уведомления
        print("\n📧 Тест 1: Отправка тестового уведомления...")
        result = await send_test_notification(
            telegram_id=test_telegram_id,
            notification_type=NotificationType.OVULATION_DAY,
            bot=bot
        )

        if result:
            print("✅ Тестовое уведомление отправлено успешно")
        else:
            print("❌ Ошибка отправки тестового уведомления")

        # Тест 2: Отправка реального уведомления через основную функцию
        print("\n📧 Тест 2: Отправка уведомления через send_notification...")
        result = await send_notification(
            user_id=user.id,
            notification_type=NotificationType.PERIOD_REMINDER,
            bot=bot
        )

        if result:
            print("✅ Уведомление отправлено успешно")
        else:
            print("❌ Ошибка отправки уведомления")

        # Тест 3: Проверка записи в notification_log
        print("\n📝 Тест 3: Проверка записи в notification_log...")
        logs = get_notification_logs(user_id=user.id, limit=5, session=db)

        if logs:
            print(f"✅ Найдено {len(logs)} записей в логе:")
            for log in logs:
                print(f"   - {log.notification_type}: {log.status} ({log.sent_at})")
        else:
            print("⚠️ Записи в notification_log не найдены")

        # Тест 4: Синхронная отправка
        print("\n📧 Тест 4: Синхронная отправка уведомления...")
        result = send_notification_sync(
            user_id=user.id,
            notification_type=NotificationType.FERTILE_WINDOW_START,
            bot=bot
        )

        if result:
            print("✅ Синхронная отправка работает")
        else:
            print("❌ Ошибка синхронной отправки")

        # Тест 5: Попытка отправки несуществующему пользователю
        print("\n📧 Тест 5: Попытка отправки несуществующему пользователю...")
        result = await send_notification(
            user_id=99999,  # Несуществующий ID
            notification_type=NotificationType.PERIOD_START,
            bot=bot
        )

        if not result:
            print("✅ Корректная обработка несуществующего пользователя")
        else:
            print("❌ Неожиданный успех для несуществующего пользователя")

        print("\n" + "="*60)
        print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("="*60)

        print("\nПРИМЕЧАНИЯ:")
        print("1. Проверьте свой Telegram - вы должны получить тестовые уведомления")
        print("2. Для теста rate limiting нужно отправить много сообщений подряд")
        print("3. Для теста блокировки - заблокируйте бота и запустите тест снова")

    finally:
        db.close()


async def test_rate_limiting():
    """Тест обработки rate limiting (требует отправки многих сообщений)."""

    from telegram import Bot
    from notifications.types import NotificationType
    from notifications.sender import send_notification
    from database.crud import get_user_by_telegram_id
    from database.session import get_db

    bot_token = os.getenv('BOT_TOKEN')
    test_telegram_id = int(os.getenv('TEST_TELEGRAM_ID', '0'))

    if not bot_token or test_telegram_id == 0:
        logger.error("Настройте BOT_TOKEN и TEST_TELEGRAM_ID в .env")
        return

    bot = Bot(token=bot_token)
    db = next(get_db())

    try:
        user = get_user_by_telegram_id(test_telegram_id, session=db)
        if not user:
            print("Пользователь не найден")
            return

        print("\n" + "="*60)
        print("ТЕСТ RATE LIMITING")
        print("="*60)
        print("Отправка множества сообщений для вызова rate limiting...")
        print("(Telegram может ограничить после ~30 сообщений в секунду)")

        # Отправляем много сообщений подряд
        for i in range(50):
            print(f"Отправка {i+1}/50...", end=" ")
            result = await send_notification(
                user_id=user.id,
                notification_type=NotificationType.OVULATION_DAY,
                bot=bot
            )
            if result:
                print("✅")
            else:
                print("❌")

            # Небольшая задержка чтобы не слишком спамить
            await asyncio.sleep(0.1)

        print("\nТест rate limiting завершён")
        print("Проверьте логи на наличие сообщений о rate limiting и повторных попытках")

    finally:
        db.close()


def main():
    """Главная функция."""

    print("\nВыберите тест:")
    print("1. Основные функции отправки уведомлений")
    print("2. Тест rate limiting (отправит много сообщений)")

    choice = input("\nВаш выбор (1-2): ").strip()

    if choice == '1':
        asyncio.run(test_notification_functions())
    elif choice == '2':
        confirm = input(
            "\n⚠️ Этот тест отправит ~50 сообщений. Продолжить? (y/n): "
        ).strip().lower()
        if confirm == 'y':
            asyncio.run(test_rate_limiting())
        else:
            print("Тест отменён")
    else:
        print("Неверный выбор")


if __name__ == "__main__":
    main()