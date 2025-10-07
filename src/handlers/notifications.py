"""
Обработчик команды /notifications для управления уведомлениями.
Позволяет пользователям включать и выключать различные типы уведомлений.
"""
from utils.logger import get_logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.crud import (
    get_user,
    get_user_notification_settings,
    update_notification_setting,
    get_current_cycle
)
from notifications.types import NotificationType, get_notification_message
from notifications.scheduler_utils import (
    calculate_notification_time,
    calculate_notification_job_id
)

logger = get_logger(__name__)

# Mapping for human-readable notification names in Russian
NOTIFICATION_NAMES = {
    NotificationType.PERIOD_REMINDER: "Напоминание о месячных",
    NotificationType.PERIOD_START: "Начало месячных",
    NotificationType.FERTILE_WINDOW_START: "Начало фертильного окна",
    NotificationType.OVULATION_DAY: "День овуляции",
    NotificationType.SAFE_PERIOD: "Начало безопасного периода"
}


async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /notifications - показать меню управления уведомлениями."""
    telegram_id = update.effective_user.id

    # Получаем пользователя из БД
    user = get_user(telegram_id)
    if not user:
        await update.message.reply_text(
            "Сначала настройте свой цикл с помощью команды /setup"
        )
        return

    # Получаем текущий цикл
    current_cycle = get_current_cycle(user.id)
    if not current_cycle:
        await update.message.reply_text(
            "У вас нет активного цикла. Пожалуйста, настройте цикл с помощью команды /setup"
        )
        return

    # Получаем настройки уведомлений
    settings = get_user_notification_settings(user.id)

    # Создаем клавиатуру с кнопками для каждого типа уведомления
    keyboard = []

    for notification_type in NotificationType:
        # Проверяем статус уведомления
        setting = next(
            (s for s in settings if s.notification_type == notification_type.value),
            None
        )
        is_enabled = setting.is_enabled if setting else True

        # Символ статуса
        status_emoji = "✅" if is_enabled else "❌"

        # Текст кнопки
        button_text = f"{status_emoji} {NOTIFICATION_NAMES[notification_type]}"

        # Callback data для идентификации кнопки
        callback_data = f"toggle_notification_{notification_type.value}"

        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # Добавляем информационную кнопку
    keyboard.append([InlineKeyboardButton("ℹ️ Информация о уведомлениях", callback_data="notification_info")])
    keyboard.append([InlineKeyboardButton("🔙 Закрыть", callback_data="close_notifications")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = (
        "⚙️ <b>Управление уведомлениями</b>\n\n"
        "Выберите, какие уведомления вы хотите получать:\n\n"
        "✅ - уведомление включено\n"
        "❌ - уведомление выключено\n\n"
        "Нажмите на кнопку, чтобы изменить статус."
    )

    await update.message.reply_text(
        message_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def toggle_notification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатия на кнопку переключения уведомления."""
    query = update.callback_query
    await query.answer()

    # Извлекаем тип уведомления из callback_data
    callback_data = query.data
    if not callback_data.startswith("toggle_notification_"):
        return

    notification_type_value = callback_data.replace("toggle_notification_", "")

    # Получаем пользователя
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    if not user:
        await query.answer("Ошибка: пользователь не найден", show_alert=True)
        return

    # Получаем текущий цикл
    current_cycle = get_current_cycle(user.id)
    if not current_cycle:
        await query.answer("Ошибка: нет активного цикла", show_alert=True)
        return

    # Получаем текущий статус уведомления
    settings = get_user_notification_settings(user.id)
    setting = next(
        (s for s in settings if s.notification_type == notification_type_value),
        None
    )

    # Определяем новый статус
    current_status = setting.is_enabled if setting else True
    new_status = not current_status

    # Обновляем настройку в БД
    update_notification_setting(user.id, notification_type_value, new_status)

    # Получаем scheduler из контекста
    scheduler = context.bot_data.get('scheduler')

    if scheduler:
        # Генерируем ID задачи
        job_id = calculate_notification_job_id(user.id, notification_type_value)

        if new_status:
            # Включаем уведомление - добавляем задачу в scheduler
            try:
                # Находим соответствующий тип уведомления
                notification_type = None
                for nt in NotificationType:
                    if nt.value == notification_type_value:
                        notification_type = nt
                        break

                if notification_type:
                    # Рассчитываем время уведомления
                    notification_datetime = calculate_notification_time(
                        current_cycle,
                        notification_type,
                        user.timezone
                    )

                    if notification_datetime:
                        # Добавляем задачу в планировщик
                        await scheduler.add_notification_task(
                            user_id=user.id,
                            notification_type=notification_type,
                            run_date=notification_datetime,
                            context=context
                        )
                        logger.info(f"Enabled notification {notification_type_value} for user {user.id}")
            except Exception as e:
                logger.error(f"Error enabling notification: {e}")
                await query.answer("Ошибка при включении уведомления", show_alert=True)
                return
        else:
            # Выключаем уведомление - удаляем задачу из scheduler
            try:
                scheduler.remove_job(job_id)
                logger.info(f"Disabled notification {notification_type_value} for user {user.id}")
            except Exception as e:
                # Задача может не существовать, это нормально
                logger.debug(f"Could not remove job {job_id}: {e}")

    # Обновляем клавиатуру
    settings = get_user_notification_settings(user.id)
    keyboard = []

    for notification_type in NotificationType:
        setting = next(
            (s for s in settings if s.notification_type == notification_type.value),
            None
        )
        is_enabled = setting.is_enabled if setting else True
        status_emoji = "✅" if is_enabled else "❌"
        button_text = f"{status_emoji} {NOTIFICATION_NAMES[notification_type]}"
        callback_data = f"toggle_notification_{notification_type.value}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("ℹ️ Информация о уведомлениях", callback_data="notification_info")])
    keyboard.append([InlineKeyboardButton("🔙 Закрыть", callback_data="close_notifications")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение
    await query.edit_message_reply_markup(reply_markup=reply_markup)

    # Показываем уведомление об изменении
    notification_name = NOTIFICATION_NAMES.get(
        next((nt for nt in NotificationType if nt.value == notification_type_value), None),
        "Уведомление"
    )
    status_text = "включено ✅" if new_status else "выключено ❌"
    await query.answer(f"{notification_name} {status_text}")


async def notification_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать информацию о типах уведомлений."""
    query = update.callback_query
    await query.answer()

    info_text = "📋 <b>Информация о уведомлениях:</b>\n\n"

    for notification_type in NotificationType:
        name = NOTIFICATION_NAMES[notification_type]
        description = get_notification_message(notification_type)
        info_text += f"<b>{name}:</b>\n{description}\n\n"

    # Кнопка для возврата
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_notifications")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        info_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def back_to_notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вернуться к главному меню управления уведомлениями."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    if not user:
        return

    # Получаем настройки уведомлений
    settings = get_user_notification_settings(user.id)

    # Создаем клавиатуру
    keyboard = []

    for notification_type in NotificationType:
        setting = next(
            (s for s in settings if s.notification_type == notification_type.value),
            None
        )
        is_enabled = setting.is_enabled if setting else True
        status_emoji = "✅" if is_enabled else "❌"
        button_text = f"{status_emoji} {NOTIFICATION_NAMES[notification_type]}"
        callback_data = f"toggle_notification_{notification_type.value}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("ℹ️ Информация о уведомлениях", callback_data="notification_info")])
    keyboard.append([InlineKeyboardButton("🔙 Закрыть", callback_data="close_notifications")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = (
        "⚙️ <b>Управление уведомлениями</b>\n\n"
        "Выберите, какие уведомления вы хотите получать:\n\n"
        "✅ - уведомление включено\n"
        "❌ - уведомление выключено\n\n"
        "Нажмите на кнопку, чтобы изменить статус."
    )

    await query.edit_message_text(
        message_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def close_notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Закрыть меню уведомлений."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Настройки уведомлений сохранены.")


def setup_notifications_handlers(application):
    """Регистрация обработчиков для управления уведомлениями."""
    # Команда /notifications
    application.add_handler(CommandHandler("notifications", notifications_command))

    # Callback обработчики
    application.add_handler(CallbackQueryHandler(
        toggle_notification_callback,
        pattern="^toggle_notification_"
    ))
    application.add_handler(CallbackQueryHandler(
        notification_info_callback,
        pattern="^notification_info$"
    ))
    application.add_handler(CallbackQueryHandler(
        back_to_notifications_callback,
        pattern="^back_to_notifications$"
    ))
    application.add_handler(CallbackQueryHandler(
        close_notifications_callback,
        pattern="^close_notifications$"
    ))