#!/usr/bin/env python3
"""
Скрипт для проверки токена бота после регистрации.
Запускать из корня проекта: python src/utils/verify_bot_token.py
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
import asyncio

# Загружаем переменные окружения
load_dotenv()


async def verify_bot_token():
    """Проверяет, что токен бота настроен и валиден."""
    token = os.getenv("BOT_TOKEN")

    if not token or token == "YOUR_BOT_TOKEN_HERE_REPLACE_ME":
        print("❌ Ошибка: Токен бота не настроен!")
        print("\nИнструкции:")
        print("1. Откройте Telegram и найдите @BotFather")
        print("2. Создайте нового бота командой /newbot")
        print("3. Скопируйте полученный токен")
        print("4. Откройте файл .env в корне проекта")
        print("5. Замените YOUR_BOT_TOKEN_HERE_REPLACE_ME на реальный токен")
        print("\nПодробные инструкции: documentation/bot_registration_instructions.md")
        return False

    try:
        from telegram import Bot
        from telegram.error import InvalidToken, TelegramError

        bot = Bot(token=token)
        bot_info = await bot.get_me()

        print("✅ Токен бота валиден!")
        print(f"\nИнформация о боте:")
        print(f"  Username: @{bot_info.username}")
        print(f"  Имя: {bot_info.first_name}")
        print(f"  ID: {bot_info.id}")
        print(f"  Может присоединяться к группам: {bot_info.can_join_groups}")
        print(f"  Может читать все сообщения: {bot_info.can_read_all_group_messages}")

        print("\n✅ Бот готов к использованию!")
        return True

    except InvalidToken:
        print("❌ Ошибка: Недействительный токен!")
        print("Проверьте правильность токена в файле .env")
        return False
    except ImportError:
        print("❌ Ошибка: Библиотека python-telegram-bot не установлена!")
        print("Выполните: pip install python-telegram-bot")
        return False
    except TelegramError as e:
        print(f"❌ Ошибка Telegram API: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(verify_bot_token())