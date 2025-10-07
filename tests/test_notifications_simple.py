"""
Упрощенные тесты для системы уведомлений.
Фокус на проверке основных функций без сложных зависимостей.
"""

import unittest
from datetime import datetime, date, time, timedelta
from unittest.mock import Mock, MagicMock, patch
import pytz

# Импорты из проекта
from src.notifications.types import (
    NotificationType,
    get_notification_message,
    get_notification_offset,
    get_notification_display_name,
    get_notification_emoji,
    calculate_notification_datetime as calc_notification_datetime_types
)


class TestNotificationTypes(unittest.TestCase):
    """Тесты для типов уведомлений."""

    def test_notification_types_exist(self):
        """Проверка, что все типы уведомлений определены."""
        expected_types = [
            'PERIOD_REMINDER',
            'PERIOD_START',
            'FERTILE_WINDOW_START',
            'OVULATION_DAY',
            'SAFE_PERIOD'
        ]

        for type_name in expected_types:
            self.assertTrue(hasattr(NotificationType, type_name))
            self.assertIsNotNone(getattr(NotificationType, type_name))

    def test_get_notification_message(self):
        """Проверка получения текста уведомления."""
        for notification_type in NotificationType:
            text = get_notification_message(notification_type)
            self.assertIsNotNone(text)
            self.assertIsInstance(text, str)
            self.assertGreater(len(text), 0)

    def test_get_notification_offset(self):
        """Проверка получения временного смещения."""
        # Проверяем PERIOD_REMINDER - должно быть за 2 дня до
        offset = get_notification_offset(NotificationType.PERIOD_REMINDER)
        self.assertEqual(offset, timedelta(days=-2))

        # Проверяем остальные типы - должны быть в день события
        for nt in [NotificationType.PERIOD_START, NotificationType.OVULATION_DAY]:
            offset = get_notification_offset(nt)
            self.assertEqual(offset, timedelta(days=0))

    def test_get_notification_display_name(self):
        """Проверка получения отображаемого имени."""
        for notification_type in NotificationType:
            name = get_notification_display_name(notification_type)
            self.assertIsNotNone(name)
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)

    def test_get_notification_emoji(self):
        """Проверка получения эмодзи."""
        emoji_map = {
            NotificationType.PERIOD_REMINDER: "🔔",
            NotificationType.PERIOD_START: "🩸",
            NotificationType.FERTILE_WINDOW_START: "🌸",
            NotificationType.OVULATION_DAY: "🎯",
            NotificationType.SAFE_PERIOD: "✅"
        }

        for notification_type, expected_emoji in emoji_map.items():
            emoji = get_notification_emoji(notification_type)
            self.assertEqual(emoji, expected_emoji)


class TestNotificationDateTimeCalculation(unittest.TestCase):
    """Тесты для расчета даты и времени уведомлений из модуля types."""

    def test_calculate_notification_datetime_from_types(self):
        """Тест функции calculate_notification_datetime из модуля types."""
        event_date = date(2025, 10, 15)

        # Тест с дефолтным временем
        result = calc_notification_datetime_types(
            event_date,
            NotificationType.PERIOD_REMINDER
        )

        # PERIOD_REMINDER имеет смещение -2 дня
        expected_date = date(2025, 10, 13)
        self.assertEqual(result.date(), expected_date)
        self.assertEqual(result.time(), time(9, 0))  # Дефолтное время

    def test_calculate_notification_datetime_with_custom_time(self):
        """Тест с пользовательским временем."""
        event_date = date(2025, 10, 15)
        custom_time = {'hour': 14, 'minute': 30}

        result = calc_notification_datetime_types(
            event_date,
            NotificationType.OVULATION_DAY,
            custom_time
        )

        # OVULATION_DAY имеет смещение 0 дней
        self.assertEqual(result.date(), event_date)
        self.assertEqual(result.time(), time(14, 30))


class TestSchedulerUtilsBasic(unittest.TestCase):
    """Базовые тесты для утилит планировщика."""

    @patch('src.notifications.scheduler_utils.datetime')
    def test_calculate_notification_datetime(self, mock_datetime):
        """Тест базовой функции расчета datetime с учетом часового пояса."""
        from src.notifications.scheduler_utils import calculate_notification_datetime

        base_date = date(2025, 10, 1)
        default_time = time(9, 0)
        timezone = 'Europe/Moscow'

        # Настраиваем мок для datetime.combine
        mock_datetime.combine = datetime.combine

        result = calculate_notification_datetime(
            base_date, default_time, timezone
        )

        self.assertIsInstance(result, datetime)
        self.assertEqual(result.date(), base_date)
        self.assertEqual(result.time(), default_time)
        self.assertEqual(result.tzinfo, pytz.timezone(timezone))


class TestNotificationJobIds(unittest.TestCase):
    """Тесты для работы с ID задач планировщика."""

    def test_calculate_and_parse_job_id(self):
        """Тест генерации и парсинга ID задачи."""
        from src.notifications.scheduler_utils import (
            calculate_notification_job_id,
            parse_notification_job_id
        )

        user_id = 123
        notification_type = NotificationType.OVULATION_DAY

        # Генерируем ID
        job_id = calculate_notification_job_id(user_id, notification_type)

        self.assertIsInstance(job_id, str)
        self.assertIn(str(user_id), job_id)
        self.assertIn(notification_type.value, job_id)

        # Парсим обратно
        parsed_user_id, parsed_type = parse_notification_job_id(job_id)

        self.assertEqual(parsed_user_id, user_id)
        self.assertEqual(parsed_type, notification_type)


class TestSchedulerClass(unittest.TestCase):
    """Тесты для класса NotificationScheduler."""

    @patch('src.notifications.scheduler.AsyncIOScheduler')
    @patch('src.notifications.scheduler.SQLAlchemyJobStore')
    def test_scheduler_initialization(self, mock_jobstore, mock_scheduler_class):
        """Тест инициализации планировщика."""
        from src.notifications.scheduler import NotificationScheduler

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        bot = Mock()
        scheduler = NotificationScheduler(bot)

        self.assertIsNotNone(scheduler.scheduler)
        self.assertEqual(scheduler.bot, bot)
        mock_scheduler_class.assert_called_once()

    @patch('src.notifications.scheduler.AsyncIOScheduler')
    def test_add_notification_job(self, mock_scheduler_class):
        """Тест добавления задачи уведомления."""
        from src.notifications.scheduler import NotificationScheduler

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        bot = Mock()
        scheduler = NotificationScheduler(bot)

        user_id = 123
        notification_type = NotificationType.PERIOD_REMINDER
        run_date = datetime.now() + timedelta(days=1)

        scheduler.add_notification_job(user_id, notification_type, run_date)

        mock_scheduler.add_job.assert_called_once()
        args, kwargs = mock_scheduler.add_job.call_args

        self.assertEqual(kwargs['trigger'], 'date')
        self.assertEqual(kwargs['run_date'], run_date)
        self.assertIn(str(user_id), kwargs['id'])

    @patch('src.notifications.scheduler.AsyncIOScheduler')
    def test_remove_user_jobs(self, mock_scheduler_class):
        """Тест удаления всех задач пользователя."""
        from src.notifications.scheduler import NotificationScheduler

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        user_id = 123

        # Создаем моковые задачи
        job1 = Mock()
        job1.id = f"notification_{user_id}_OVULATION_DAY"
        job2 = Mock()
        job2.id = f"notification_{user_id}_PERIOD_REMINDER"
        job3 = Mock()
        job3.id = "notification_456_OVULATION_DAY"  # Другой пользователь

        mock_scheduler.get_jobs.return_value = [job1, job2, job3]

        bot = Mock()
        scheduler = NotificationScheduler(bot)
        scheduler.remove_user_jobs(user_id)

        # Должны быть удалены только задачи пользователя 123
        self.assertEqual(mock_scheduler.remove_job.call_count, 2)


if __name__ == '__main__':
    unittest.main()