"""
Модуль определения типов уведомлений для менструального цикла.

Содержит перечисление типов уведомлений, их текстовые шаблоны
и временные смещения для планирования отправки.
"""

from enum import Enum
from typing import Dict, Optional
from datetime import timedelta


class NotificationType(Enum):
    """Перечисление типов уведомлений о менструальном цикле."""

    PERIOD_REMINDER = "period_reminder"  # Напоминание о приближении месячных
    PERIOD_START = "period_start"  # Уведомление о начале месячных
    FERTILE_WINDOW_START = "fertile_window_start"  # Начало фертильного окна
    OVULATION_DAY = "ovulation_day"  # День овуляции
    SAFE_PERIOD = "safe_period"  # Начало безопасного периода


# Текстовые шаблоны для каждого типа уведомления
NOTIFICATION_MESSAGES: Dict[NotificationType, str] = {
    NotificationType.PERIOD_REMINDER: (
        "🔔 Напоминание\n\n"
        "Через 2 дня начнутся месячные.\n"
        "Убедитесь, что у вас есть все необходимые средства гигиены.\n\n"
        "💊 Если вы испытываете предменструальные симптомы, "
        "самое время позаботиться о себе."
    ),

    NotificationType.PERIOD_START: (
        "🩸 Начало менструации\n\n"
        "Сегодня ожидаемый день начала месячных.\n"
        "Отметьте фактическую дату начала, если она отличается.\n\n"
        "💙 Будьте внимательны к своему самочувствию и "
        "не забывайте отдыхать при необходимости."
    ),

    NotificationType.FERTILE_WINDOW_START: (
        "🌸 Начало фертильного периода\n\n"
        "Сегодня начинается ваше фертильное окно.\n"
        "Следующие 6-7 дней - наиболее благоприятное время для зачатия.\n\n"
        "📊 Вероятность беременности в эти дни максимальна."
    ),

    NotificationType.OVULATION_DAY: (
        "🎯 День овуляции\n\n"
        "Сегодня предполагаемый день овуляции.\n"
        "Это пик вашей фертильности в текущем цикле.\n\n"
        "🌡️ Возможные признаки: изменение базальной температуры, "
        "изменение цервикальной слизи, легкая боль внизу живота."
    ),

    NotificationType.SAFE_PERIOD: (
        "✅ Начало безопасного периода\n\n"
        "Фертильное окно завершилось.\n"
        "Вероятность зачатия в последующие дни минимальна.\n\n"
        "📝 Помните, что это приблизительные расчеты. "
        "Для надежной контрацепции используйте дополнительные методы."
    )
}


# Временные смещения для каждого типа уведомления
# Отрицательные значения означают "за X дней до события"
# Положительные значения означают "через X дней после события"
NOTIFICATION_OFFSETS: Dict[NotificationType, timedelta] = {
    NotificationType.PERIOD_REMINDER: timedelta(days=-2),  # За 2 дня до начала месячных
    NotificationType.PERIOD_START: timedelta(days=0),  # В день начала месячных
    NotificationType.FERTILE_WINDOW_START: timedelta(days=0),  # В день начала фертильного окна
    NotificationType.OVULATION_DAY: timedelta(days=0),  # В день овуляции
    NotificationType.SAFE_PERIOD: timedelta(days=0)  # В день начала безопасного периода
}


# Время отправки уведомлений по умолчанию (в часах и минутах)
DEFAULT_NOTIFICATION_TIME = {
    'hour': 9,  # 9:00 утра
    'minute': 0
}


def get_notification_message(notification_type: NotificationType) -> str:
    """
    Получить текст сообщения для указанного типа уведомления.

    Args:
        notification_type: Тип уведомления

    Returns:
        Текст сообщения для отправки пользователю
    """
    return NOTIFICATION_MESSAGES.get(
        notification_type,
        "📬 У вас есть новое уведомление о вашем цикле."
    )


def get_notification_offset(notification_type: NotificationType) -> timedelta:
    """
    Получить временное смещение для указанного типа уведомления.

    Args:
        notification_type: Тип уведомления

    Returns:
        Временное смещение относительно события
    """
    return NOTIFICATION_OFFSETS.get(notification_type, timedelta(days=0))


def get_notification_display_name(notification_type: NotificationType) -> str:
    """
    Получить человекочитаемое название для типа уведомления.

    Args:
        notification_type: Тип уведомления

    Returns:
        Название уведомления для отображения пользователю
    """
    display_names = {
        NotificationType.PERIOD_REMINDER: "Напоминание о месячных (за 2 дня)",
        NotificationType.PERIOD_START: "Начало месячных",
        NotificationType.FERTILE_WINDOW_START: "Начало фертильного периода",
        NotificationType.OVULATION_DAY: "День овуляции",
        NotificationType.SAFE_PERIOD: "Начало безопасного периода"
    }
    return display_names.get(notification_type, "Уведомление")


def get_notification_emoji(notification_type: NotificationType) -> str:
    """
    Получить эмодзи для типа уведомления.

    Args:
        notification_type: Тип уведомления

    Returns:
        Эмодзи для визуального отображения
    """
    emojis = {
        NotificationType.PERIOD_REMINDER: "🔔",
        NotificationType.PERIOD_START: "🩸",
        NotificationType.FERTILE_WINDOW_START: "🌸",
        NotificationType.OVULATION_DAY: "🎯",
        NotificationType.SAFE_PERIOD: "✅"
    }
    return emojis.get(notification_type, "📬")


def get_all_notification_types() -> list[NotificationType]:
    """
    Получить список всех доступных типов уведомлений.

    Returns:
        Список всех типов уведомлений
    """
    return list(NotificationType)


def calculate_notification_datetime(event_date, notification_type: NotificationType,
                                   custom_time: Optional[Dict[str, int]] = None):
    """
    Рассчитать дату и время отправки уведомления.

    Args:
        event_date: Дата события (например, начало месячных)
        notification_type: Тип уведомления
        custom_time: Пользовательское время отправки {'hour': X, 'minute': Y}

    Returns:
        datetime объект с датой и временем отправки уведомления
    """
    from datetime import datetime, time

    # Получаем смещение для типа уведомления
    offset = get_notification_offset(notification_type)

    # Вычисляем дату отправки
    notification_date = event_date + offset

    # Определяем время отправки
    notification_time_dict = custom_time or DEFAULT_NOTIFICATION_TIME
    notification_time = time(
        hour=notification_time_dict['hour'],
        minute=notification_time_dict['minute']
    )

    # Комбинируем дату и время
    return datetime.combine(notification_date, notification_time)