"""
Утилиты для планировщика уведомлений.
Функции расчета времени отправки уведомлений с учетом часовых поясов.
"""

from datetime import datetime, time, timedelta, date
from typing import Optional, List, Dict, Tuple
import pytz
from notifications.types import NotificationType, NOTIFICATION_OFFSETS, DEFAULT_NOTIFICATION_TIME
from models import User, Cycle, NotificationSettings
from utils.cycle_calculator import (
    calculate_ovulation,
    calculate_fertile_window,
    calculate_next_period,
    calculate_safe_periods
)


def calculate_notification_datetime(
    base_date: date,
    notification_time: time,
    timezone: str = 'Europe/Moscow',
    offset_days: int = 0
) -> datetime:
    """
    Рассчитать дату и время уведомления с учетом часового пояса.

    Args:
        base_date: Базовая дата для расчета
        notification_time: Время отправки уведомления
        timezone: Часовой пояс пользователя
        offset_days: Смещение в днях от базовой даты

    Returns:
        datetime: Дата и время уведомления в указанном часовом поясе
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.timezone('Europe/Moscow')

    # Добавляем смещение к базовой дате
    target_date = base_date + timedelta(days=offset_days)

    # Создаем datetime с учетом часового пояса
    dt = datetime.combine(target_date, notification_time)
    localized_dt = tz.localize(dt)

    return localized_dt


def calculate_notification_time(
    notification_type: NotificationType,
    cycle: Cycle,
    user_timezone: str = 'Europe/Moscow',
    custom_time: Optional[time] = None
) -> Optional[datetime]:
    """
    Рассчитать время отправки уведомления для конкретного типа.

    Args:
        notification_type: Тип уведомления
        cycle: Текущий цикл пользователя
        user_timezone: Часовой пояс пользователя
        custom_time: Пользовательское время отправки (если настроено)

    Returns:
        datetime: Время отправки уведомления или None если уведомление в прошлом
    """
    if not cycle or not cycle.is_current:
        return None

    # Получаем время отправки (пользовательское или дефолтное)
    send_time = custom_time or DEFAULT_NOTIFICATION_TIME.get(notification_type, time(9, 0))

    # Получаем смещение для типа уведомления (timedelta)
    offset_timedelta = NOTIFICATION_OFFSETS.get(notification_type, timedelta(days=0))
    offset_days = offset_timedelta.days

    # Рассчитываем базовую дату в зависимости от типа уведомления
    if notification_type == NotificationType.PERIOD_REMINDER:
        # За 2 дня до следующих месячных
        next_period = calculate_next_period(cycle.start_date, cycle.cycle_length)
        base_date = next_period
        offset_days = -2

    elif notification_type == NotificationType.PERIOD_START:
        # В день начала следующих месячных
        base_date = calculate_next_period(cycle.start_date, cycle.cycle_length)
        offset_days = 0

    elif notification_type == NotificationType.FERTILE_WINDOW_START:
        # Начало фертильного окна
        ovulation = calculate_ovulation(cycle.start_date, cycle.cycle_length)
        fertile_start, _ = calculate_fertile_window(ovulation)
        base_date = fertile_start
        offset_days = 0

    elif notification_type == NotificationType.OVULATION_DAY:
        # День овуляции
        base_date = calculate_ovulation(cycle.start_date, cycle.cycle_length)
        offset_days = 0

    elif notification_type == NotificationType.SAFE_PERIOD:
        # Начало безопасного периода (после фертильного окна)
        ovulation = calculate_ovulation(cycle.start_date, cycle.cycle_length)
        _, fertile_end = calculate_fertile_window(ovulation)
        base_date = fertile_end
        offset_days = 1  # День после окончания фертильного окна

    else:
        return None

    # Рассчитываем datetime уведомления
    notification_dt = calculate_notification_datetime(
        base_date, send_time, user_timezone, offset_days
    )

    # Проверяем, что уведомление в будущем
    now = datetime.now(pytz.timezone(user_timezone))
    if notification_dt <= now:
        # Если уведомление в прошлом, пробуем рассчитать для следующего цикла
        next_cycle_start = cycle.start_date + timedelta(days=cycle.cycle_length)
        if notification_type in [NotificationType.PERIOD_REMINDER, NotificationType.PERIOD_START]:
            # Для уведомлений о месячных используем следующий цикл
            next_period = next_cycle_start + timedelta(days=cycle.cycle_length)
            base_date = next_period
            notification_dt = calculate_notification_datetime(
                base_date, send_time, user_timezone, offset_days
            )

        # Проверяем еще раз
        if notification_dt <= now:
            return None

    return notification_dt


def get_all_notification_times(
    cycle: Cycle,
    user: User,
    notification_settings: Optional[List[NotificationSettings]] = None
) -> Dict[NotificationType, datetime]:
    """
    Получить время отправки всех уведомлений для пользователя.

    Args:
        cycle: Текущий цикл пользователя
        user: Пользователь
        notification_settings: Настройки уведомлений пользователя

    Returns:
        Dict: Словарь {тип_уведомления: время_отправки}
    """
    notifications = {}
    user_timezone = user.timezone or 'Europe/Moscow'

    # Создаем словарь настроек для быстрого доступа
    settings_dict = {}
    if notification_settings:
        settings_dict = {
            setting.notification_type: setting
            for setting in notification_settings
        }

    # Рассчитываем время для каждого типа уведомления
    for notification_type in NotificationType:
        # Проверяем, включено ли уведомление
        setting = settings_dict.get(notification_type)
        if setting and not setting.is_enabled:
            continue

        # Получаем пользовательское время если настроено
        custom_time = None
        if setting and setting.time_offset:
            # time_offset хранит минуты смещения от полуночи
            hours = setting.time_offset // 60
            minutes = setting.time_offset % 60
            custom_time = time(hours, minutes)

        # Рассчитываем время уведомления
        notification_time = calculate_notification_time(
            notification_type, cycle, user_timezone, custom_time
        )

        if notification_time:
            notifications[notification_type] = notification_time

    return notifications


def get_next_notification(
    cycle: Cycle,
    user: User,
    notification_settings: Optional[List[NotificationSettings]] = None
) -> Optional[Tuple[NotificationType, datetime]]:
    """
    Получить следующее уведомление для отправки.

    Args:
        cycle: Текущий цикл пользователя
        user: Пользователь
        notification_settings: Настройки уведомлений пользователя

    Returns:
        Tuple: (тип_уведомления, время_отправки) или None
    """
    all_notifications = get_all_notification_times(cycle, user, notification_settings)

    if not all_notifications:
        return None

    # Находим ближайшее уведомление
    now = datetime.now(pytz.timezone(user.timezone or 'Europe/Moscow'))
    future_notifications = [
        (nt, dt) for nt, dt in all_notifications.items() if dt > now
    ]

    if not future_notifications:
        return None

    # Сортируем по времени и возвращаем первое
    future_notifications.sort(key=lambda x: x[1])
    return future_notifications[0]


def should_send_notification_now(
    notification_type: NotificationType,
    cycle: Cycle,
    user: User,
    tolerance_minutes: int = 30
) -> bool:
    """
    Проверить, нужно ли отправить уведомление прямо сейчас.

    Args:
        notification_type: Тип уведомления
        cycle: Текущий цикл
        user: Пользователь
        tolerance_minutes: Допустимое отклонение в минутах

    Returns:
        bool: True если нужно отправить уведомление
    """
    notification_time = calculate_notification_time(
        notification_type, cycle, user.timezone or 'Europe/Moscow'
    )

    if not notification_time:
        return False

    now = datetime.now(pytz.timezone(user.timezone or 'Europe/Moscow'))
    time_diff = abs((notification_time - now).total_seconds() / 60)

    return time_diff <= tolerance_minutes


def reschedule_notifications_for_cycle(
    cycle: Cycle,
    user: User,
    notification_settings: Optional[List[NotificationSettings]] = None
) -> List[Tuple[NotificationType, datetime]]:
    """
    Пересчитать все уведомления при изменении параметров цикла.

    Args:
        cycle: Обновленный цикл
        user: Пользователь
        notification_settings: Настройки уведомлений

    Returns:
        List: Список кортежей (тип_уведомления, новое_время)
    """
    all_notifications = get_all_notification_times(cycle, user, notification_settings)

    # Фильтруем только будущие уведомления
    now = datetime.now(pytz.timezone(user.timezone or 'Europe/Moscow'))
    future_notifications = [
        (nt, dt) for nt, dt in all_notifications.items() if dt > now
    ]

    # Сортируем по времени
    future_notifications.sort(key=lambda x: x[1])

    return future_notifications


def calculate_notification_job_id(user_id: int, notification_type: NotificationType) -> str:
    """
    Сгенерировать уникальный ID для задачи планировщика.

    Args:
        user_id: ID пользователя
        notification_type: Тип уведомления

    Returns:
        str: Уникальный ID задачи
    """
    return f"notification_{user_id}_{notification_type.value}"


def parse_notification_job_id(job_id: str) -> Optional[Tuple[int, NotificationType]]:
    """
    Распарсить ID задачи планировщика.

    Args:
        job_id: ID задачи

    Returns:
        Tuple: (user_id, notification_type) или None
    """
    try:
        parts = job_id.split('_', 2)  # Разделить на максимум 3 части
        if len(parts) != 3 or parts[0] != 'notification':
            return None

        user_id = int(parts[1])

        # Пробуем найти соответствующий тип уведомления
        notification_type = None
        for nt in NotificationType:
            if nt.value == parts[2]:
                notification_type = nt
                break

        if notification_type is None:
            return None

        return user_id, notification_type
    except (ValueError, KeyError):
        return None