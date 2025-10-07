"""
Модуль для расчёта ключевых дат менструального цикла.

Этот модуль содержит функции для расчёта овуляции, фертильного окна,
безопасных периодов и других важных дат цикла с учётом часовых поясов.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from zoneinfo import ZoneInfo

try:
    from models.cycle import Cycle
except ImportError:
    # This will happen when importing from tests or when there are circular imports
    Cycle = None

logger = logging.getLogger(__name__)


def calculate_ovulation(start_date: date, cycle_length: int) -> date:
    """
    Рассчитать предполагаемую дату овуляции.

    Алгоритм: Овуляция обычно происходит за 14 дней до начала следующих месячных.
    Формула: start_date + cycle_length - 14

    Args:
        start_date: Дата начала последних месячных
        cycle_length: Длина цикла в днях (21-40)

    Returns:
        Предполагаемая дата овуляции

    Note:
        Это приблизительная оценка. У разных женщин овуляция может происходить
        в разное время цикла, и даже у одной женщины это может варьироваться.
    """
    if not 21 <= cycle_length <= 40:
        logger.warning(f"Необычная длина цикла: {cycle_length} дней")

    ovulation_day = cycle_length - 14
    ovulation_date = start_date + timedelta(days=ovulation_day)

    logger.debug(f"Овуляция рассчитана на {ovulation_date} (день {ovulation_day} цикла)")
    return ovulation_date


def calculate_fertile_window(ovulation_date: date) -> Tuple[date, date]:
    """
    Рассчитать фертильное окно (период возможной беременности).

    Алгоритм: Фертильное окно включает 5 дней до овуляции и 1 день после.
    Сперматозоиды могут жить в женском организме до 5 дней,
    а яйцеклетка жизнеспособна около 24 часов после овуляции.

    Args:
        ovulation_date: Предполагаемая дата овуляции

    Returns:
        Кортеж (начало_фертильного_окна, конец_фертильного_окна)
    """
    fertile_start = ovulation_date - timedelta(days=5)
    fertile_end = ovulation_date + timedelta(days=1)

    logger.debug(f"Фертильное окно: с {fertile_start} по {fertile_end}")
    return fertile_start, fertile_end


def calculate_safe_periods(
    start_date: date,
    cycle_length: int,
    period_length: int
) -> Tuple[Optional[Tuple[date, date]], Optional[Tuple[date, date]]]:
    """
    Рассчитать безопасные периоды (с низкой вероятностью зачатия).

    Алгоритм: Безопасными считаются периоды вне фертильного окна.
    Учитываем дополнительный запас в 2-3 дня для надежности.

    Args:
        start_date: Дата начала последних месячных
        cycle_length: Длина цикла в днях
        period_length: Длительность месячных в днях

    Returns:
        Кортеж из двух периодов: (первый_безопасный_период, второй_безопасный_период)
        Каждый период - это кортеж (начало, конец) или None если период отсутствует

    Note:
        Календарный метод контрацепции НЕ является надёжным!
        Эти расчёты приблизительны и не должны использоваться
        как единственный метод контрацепции.
    """
    ovulation_date = calculate_ovulation(start_date, cycle_length)
    fertile_start, fertile_end = calculate_fertile_window(ovulation_date)

    # Добавляем запас в 2 дня с каждой стороны фертильного окна
    safe_margin = 2
    unsafe_start = fertile_start - timedelta(days=safe_margin)
    unsafe_end = fertile_end + timedelta(days=safe_margin)

    # Первый безопасный период: после окончания месячных до начала опасного периода
    first_safe_start = start_date + timedelta(days=period_length)
    first_safe_end = unsafe_start - timedelta(days=1)

    first_safe = None
    if first_safe_end >= first_safe_start:
        first_safe = (first_safe_start, first_safe_end)
        logger.debug(f"Первый безопасный период: с {first_safe_start} по {first_safe_end}")

    # Второй безопасный период: после опасного периода до начала следующих месячных
    second_safe_start = unsafe_end + timedelta(days=1)
    second_safe_end = start_date + timedelta(days=cycle_length - 1)

    second_safe = None
    if second_safe_end >= second_safe_start:
        second_safe = (second_safe_start, second_safe_end)
        logger.debug(f"Второй безопасный период: с {second_safe_start} по {second_safe_end}")

    return first_safe, second_safe


def calculate_next_period(start_date: date, cycle_length: int) -> date:
    """
    Рассчитать дату начала следующих месячных.

    Args:
        start_date: Дата начала последних месячных
        cycle_length: Длина цикла в днях

    Returns:
        Предполагаемая дата начала следующих месячных
    """
    next_period = start_date + timedelta(days=cycle_length)
    logger.debug(f"Следующие месячные ожидаются {next_period}")
    return next_period


def calculate_current_phase(
    start_date: date,
    cycle_length: int,
    period_length: int,
    current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Определить текущую фазу менструального цикла.

    Args:
        start_date: Дата начала последних месячных
        cycle_length: Длина цикла в днях
        period_length: Длительность месячных в днях
        current_date: Текущая дата (если не указана, используется сегодня)

    Returns:
        Словарь с информацией о текущей фазе:
        - phase: название фазы ('menstruation', 'follicular', 'ovulation', 'luteal', 'pre_menstruation')
        - day: день цикла (1-based)
        - description: описание фазы
        - is_fertile: находится ли в фертильном окне
        - is_safe: находится ли в безопасном периоде
    """
    if current_date is None:
        current_date = date.today()

    # Рассчитываем день цикла
    days_passed = (current_date - start_date).days

    # Если прошло больше дней чем длина цикла, пересчитываем от предполагаемого начала нового цикла
    while days_passed >= cycle_length:
        days_passed -= cycle_length
        start_date += timedelta(days=cycle_length)

    day_of_cycle = days_passed + 1  # День цикла начинается с 1

    # Рассчитываем ключевые даты
    ovulation_date = calculate_ovulation(start_date, cycle_length)
    fertile_start, fertile_end = calculate_fertile_window(ovulation_date)

    # Определяем фазу
    phase = ""
    description = ""

    if day_of_cycle <= period_length:
        phase = "menstruation"
        description = "Менструация"
    elif current_date < ovulation_date - timedelta(days=2):
        phase = "follicular"
        description = "Фолликулярная фаза"
    elif ovulation_date - timedelta(days=2) <= current_date <= ovulation_date + timedelta(days=2):
        phase = "ovulation"
        description = "Овуляция"
    elif current_date < start_date + timedelta(days=cycle_length - 3):
        phase = "luteal"
        description = "Лютеиновая фаза"
    else:
        phase = "pre_menstruation"
        description = "Предменструальный период"

    # Проверяем фертильность и безопасность
    is_fertile = fertile_start <= current_date <= fertile_end

    # Проверяем безопасные периоды
    is_safe = False
    first_safe, second_safe = calculate_safe_periods(start_date, cycle_length, period_length)
    if first_safe and first_safe[0] <= current_date <= first_safe[1]:
        is_safe = True
    elif second_safe and second_safe[0] <= current_date <= second_safe[1]:
        is_safe = True

    result = {
        "phase": phase,
        "day": day_of_cycle,
        "description": description,
        "is_fertile": is_fertile,
        "is_safe": is_safe,
        "days_until_period": (start_date + timedelta(days=cycle_length) - current_date).days
    }

    logger.debug(f"Текущая фаза: {result}")
    return result


def calculate_cycle_dates(cycle: Cycle) -> Dict[str, Any]:
    """
    Рассчитать все ключевые даты для цикла.

    Args:
        cycle: Объект цикла из БД

    Returns:
        Словарь со всеми рассчитанными датами и периодами
    """
    ovulation = calculate_ovulation(cycle.start_date, cycle.cycle_length)
    fertile_start, fertile_end = calculate_fertile_window(ovulation)
    first_safe, second_safe = calculate_safe_periods(
        cycle.start_date,
        cycle.cycle_length,
        cycle.period_length
    )
    next_period = calculate_next_period(cycle.start_date, cycle.cycle_length)
    current_phase = calculate_current_phase(
        cycle.start_date,
        cycle.cycle_length,
        cycle.period_length
    )

    return {
        "start_date": cycle.start_date,
        "cycle_length": cycle.cycle_length,
        "period_length": cycle.period_length,
        "ovulation_date": ovulation,
        "fertile_window": {
            "start": fertile_start,
            "end": fertile_end
        },
        "safe_periods": {
            "first": first_safe,
            "second": second_safe
        },
        "next_period": next_period,
        "current_phase": current_phase
    }


# Функции для работы с часовыми поясами

def convert_date_to_user_timezone(
    dt: datetime,
    user_timezone: str = "Europe/Moscow"
) -> datetime:
    """
    Конвертировать дату/время в часовой пояс пользователя.

    Args:
        dt: Дата/время для конвертации
        user_timezone: Часовой пояс пользователя (IANA timezone)

    Returns:
        Дата/время в часовом поясе пользователя
    """
    try:
        tz = ZoneInfo(user_timezone)
        if dt.tzinfo is None:
            # Если datetime naive, считаем что это UTC
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(tz)
    except Exception as e:
        logger.error(f"Ошибка конвертации часового пояса: {e}")
        # Возвращаем оригинальную дату если что-то пошло не так
        return dt


def convert_date_from_user_timezone(
    dt: datetime,
    user_timezone: str = "Europe/Moscow"
) -> datetime:
    """
    Конвертировать дату/время из часового пояса пользователя в UTC.

    Args:
        dt: Дата/время в часовом поясе пользователя
        user_timezone: Часовой пояс пользователя (IANA timezone)

    Returns:
        Дата/время в UTC
    """
    try:
        tz = ZoneInfo(user_timezone)
        if dt.tzinfo is None:
            # Если datetime naive, считаем что это в часовом поясе пользователя
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(ZoneInfo("UTC"))
    except Exception as e:
        logger.error(f"Ошибка конвертации часового пояса: {e}")
        return dt


def get_notification_datetime(
    target_date: date,
    notification_time: str = "09:00",
    user_timezone: str = "Europe/Moscow",
    days_before: int = 0
) -> datetime:
    """
    Получить дату и время для отправки уведомления с учётом часового пояса.

    Args:
        target_date: Целевая дата события
        notification_time: Время отправки уведомления (HH:MM)
        user_timezone: Часовой пояс пользователя
        days_before: За сколько дней до события отправить уведомление

    Returns:
        Дата/время отправки уведомления в UTC
    """
    # Вычисляем дату уведомления
    notification_date = target_date - timedelta(days=days_before)

    # Парсим время
    hour, minute = map(int, notification_time.split(':'))

    # Создаём datetime в часовом поясе пользователя
    tz = ZoneInfo(user_timezone)
    notification_dt = datetime(
        notification_date.year,
        notification_date.month,
        notification_date.day,
        hour,
        minute,
        tzinfo=tz
    )

    # Конвертируем в UTC для scheduler'а
    utc_dt = notification_dt.astimezone(ZoneInfo("UTC"))

    logger.debug(
        f"Уведомление запланировано на {notification_dt} "
        f"({user_timezone}) = {utc_dt} (UTC)"
    )

    return utc_dt


def is_date_in_past(
    check_date: date,
    user_timezone: str = "Europe/Moscow"
) -> bool:
    """
    Проверить, находится ли дата в прошлом с учётом часового пояса.

    Args:
        check_date: Дата для проверки
        user_timezone: Часовой пояс пользователя

    Returns:
        True если дата в прошлом, False если в будущем или сегодня
    """
    tz = ZoneInfo(user_timezone)
    now = datetime.now(tz).date()
    return check_date < now


def format_date_for_user(
    dt: date,
    user_timezone: str = "Europe/Moscow",
    include_weekday: bool = True
) -> str:
    """
    Форматировать дату для отображения пользователю.

    Args:
        dt: Дата для форматирования
        user_timezone: Часовой пояс пользователя
        include_weekday: Включить день недели в формат

    Returns:
        Отформатированная строка с датой
    """
    weekdays = {
        0: "понедельник",
        1: "вторник",
        2: "среда",
        3: "четверг",
        4: "пятница",
        5: "суббота",
        6: "воскресенье"
    }

    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }

    day = dt.day
    month = months[dt.month]
    year = dt.year

    if include_weekday:
        weekday = weekdays[dt.weekday()]
        return f"{day} {month} {year}г. ({weekday})"
    else:
        return f"{day} {month} {year}г."