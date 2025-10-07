"""
Тесты для системы уведомлений.

Этот модуль содержит тесты для:
- Расчета времени уведомлений
- Работы с APScheduler
- Функций отправки уведомлений
- Обновления задач при изменении параметров
"""

import unittest
from datetime import datetime, date, time, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
import pytz
import asyncio

# Импорты из проекта
from src.notifications.types import NotificationType, get_notification_message
from src.notifications.scheduler_utils import (
    calculate_notification_datetime,
    calculate_notification_time,
    get_all_notification_times,
    get_next_notification,
    should_send_notification_now,
    reschedule_notifications_for_cycle,
    calculate_notification_job_id,
    parse_notification_job_id
)
from src.notifications.scheduler import NotificationScheduler
from src.notifications.sender import (
    send_notification,
    send_notification_async,
    send_test_notification,
    retry_send_notification
)
from src.models.user import User
from src.models.cycle import Cycle
from src.models.notification_settings import NotificationSettings


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


class TestNotificationTimeCalculation(unittest.TestCase):
    """Тесты для расчета времени уведомлений."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.user = Mock(spec=User)
        self.user.id = 1
        self.user.telegram_id = 12345
        self.user.timezone = 'Europe/Moscow'

        self.cycle = Mock(spec=Cycle)
        self.cycle.id = 1
        self.cycle.user_id = 1
        self.cycle.start_date = date(2025, 10, 1)
        self.cycle.cycle_length = 28
        self.cycle.period_length = 5
        self.cycle.is_current = True

    def test_calculate_notification_datetime(self):
        """Тест расчета datetime с учетом часового пояса."""
        base_date = date(2025, 10, 1)
        default_time = time(9, 0)
        timezone = 'Europe/Moscow'

        result = calculate_notification_datetime(
            base_date, default_time, timezone
        )

        self.assertIsInstance(result, datetime)
        self.assertEqual(result.date(), base_date)
        self.assertEqual(result.time(), default_time)
        self.assertEqual(result.tzinfo, pytz.timezone(timezone))

    def test_calculate_notification_time_period_reminder(self):
        """Тест расчета времени напоминания о месячных."""
        with patch('src.notifications.scheduler_utils.get_user_notification_time') as mock_time:
            mock_time.return_value = time(10, 0)

            result = calculate_notification_time(
                self.user, self.cycle, NotificationType.PERIOD_REMINDER
            )

            # Напоминание за 2 дня до следующих месячных
            expected_date = date(2025, 10, 27)  # start_date + cycle_length - 2
            self.assertIsNotNone(result)
            self.assertEqual(result.date(), expected_date)
            self.assertEqual(result.time(), time(10, 0))

    def test_calculate_notification_time_ovulation(self):
        """Тест расчета времени уведомления об овуляции."""
        with patch('src.notifications.scheduler_utils.get_user_notification_time') as mock_time:
            mock_time.return_value = time(11, 0)

            result = calculate_notification_time(
                self.user, self.cycle, NotificationType.OVULATION_DAY
            )

            # Овуляция на 14-й день до конца цикла
            expected_date = date(2025, 10, 15)  # start_date + cycle_length - 14
            self.assertIsNotNone(result)
            self.assertEqual(result.date(), expected_date)
            self.assertEqual(result.time(), time(11, 0))

    def test_calculate_notification_time_fertile_window(self):
        """Тест расчета времени начала фертильного окна."""
        with patch('src.notifications.scheduler_utils.get_user_notification_time') as mock_time:
            mock_time.return_value = time(9, 30)

            result = calculate_notification_time(
                self.user, self.cycle, NotificationType.FERTILE_WINDOW_START
            )

            # Фертильное окно начинается за 5 дней до овуляции
            expected_date = date(2025, 10, 10)  # овуляция - 5 дней
            self.assertIsNotNone(result)
            self.assertEqual(result.date(), expected_date)

    def test_calculate_notification_time_safe_period(self):
        """Тест расчета времени начала безопасного периода."""
        with patch('src.notifications.scheduler_utils.get_user_notification_time') as mock_time:
            mock_time.return_value = time(8, 0)

            result = calculate_notification_time(
                self.user, self.cycle, NotificationType.SAFE_PERIOD
            )

            # Безопасный период начинается через 3 дня после овуляции
            expected_date = date(2025, 10, 18)  # овуляция + 3 дня
            self.assertIsNotNone(result)
            self.assertEqual(result.date(), expected_date)

    def test_calculate_notification_time_past_date(self):
        """Тест, что уведомления в прошлом не создаются."""
        # Устанавливаем старую дату начала цикла
        self.cycle.start_date = date(2020, 1, 1)

        with patch('src.notifications.scheduler_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 1, 12, 0, 0)
            mock_datetime.combine = datetime.combine

            result = calculate_notification_time(
                self.user, self.cycle, NotificationType.PERIOD_REMINDER
            )

            # Должно вернуть None для даты в прошлом
            self.assertIsNone(result)


class TestNotificationSchedulerUtils(unittest.TestCase):
    """Тесты для утилит планировщика уведомлений."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.user = Mock(spec=User)
        self.user.id = 1
        self.user.telegram_id = 12345
        self.user.timezone = 'Europe/Moscow'

        self.cycle = Mock(spec=Cycle)
        self.cycle.id = 1
        self.cycle.user_id = 1
        self.cycle.start_date = date(2025, 10, 1)
        self.cycle.cycle_length = 28
        self.cycle.period_length = 5
        self.cycle.is_current = True

    @patch('src.notifications.scheduler_utils.get_user_notification_time')
    def test_get_all_notification_times(self, mock_time):
        """Тест получения всех времен уведомлений."""
        mock_time.return_value = time(9, 0)

        with patch('src.notifications.scheduler_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 1, 8, 0, 0)
            mock_datetime.combine = datetime.combine

            result = get_all_notification_times(self.user, self.cycle)

            self.assertIsInstance(result, dict)
            # Должны быть все типы уведомлений
            self.assertEqual(len(result), len(NotificationType))

            # Проверяем, что все значения - datetime или None
            for notification_type, notification_time in result.items():
                self.assertIn(notification_type, NotificationType)
                if notification_time is not None:
                    self.assertIsInstance(notification_time, datetime)

    @patch('src.notifications.scheduler_utils.get_all_notification_times')
    def test_get_next_notification(self, mock_get_all):
        """Тест получения следующего уведомления."""
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        future_time = now + timedelta(days=1)
        past_time = now - timedelta(days=1)

        mock_get_all.return_value = {
            NotificationType.PERIOD_REMINDER: future_time,
            NotificationType.OVULATION_DAY: past_time,
            NotificationType.FERTILE_WINDOW_START: None
        }

        result = get_next_notification(self.user, self.cycle)

        self.assertIsNotNone(result)
        notification_type, notification_time = result
        self.assertEqual(notification_type, NotificationType.PERIOD_REMINDER)
        self.assertEqual(notification_time, future_time)

    def test_calculate_notification_job_id(self):
        """Тест генерации ID задачи для планировщика."""
        user_id = 123
        notification_type = NotificationType.OVULATION_DAY

        job_id = calculate_notification_job_id(user_id, notification_type)

        self.assertIsInstance(job_id, str)
        self.assertIn(str(user_id), job_id)
        self.assertIn(notification_type.value, job_id)

    def test_parse_notification_job_id(self):
        """Тест парсинга ID задачи планировщика."""
        job_id = "notification_123_OVULATION_DAY"

        user_id, notification_type = parse_notification_job_id(job_id)

        self.assertEqual(user_id, 123)
        self.assertEqual(notification_type, NotificationType.OVULATION_DAY)

    def test_should_send_notification_now(self):
        """Тест проверки необходимости отправки уведомления."""
        with patch('src.notifications.scheduler_utils.datetime') as mock_datetime:
            now = datetime(2025, 10, 15, 9, 0, 0)
            mock_datetime.now.return_value = now

            # Время совпадает - должно отправить
            notification_time = now
            self.assertTrue(
                should_send_notification_now(notification_time, tolerance_minutes=5)
            )

            # В пределах допуска - должно отправить
            notification_time = now - timedelta(minutes=4)
            self.assertTrue(
                should_send_notification_now(notification_time, tolerance_minutes=5)
            )

            # Вне допуска - не должно отправить
            notification_time = now - timedelta(minutes=10)
            self.assertFalse(
                should_send_notification_now(notification_time, tolerance_minutes=5)
            )


class TestNotificationScheduler(unittest.TestCase):
    """Тесты для класса NotificationScheduler."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.bot = Mock()
        self.bot.bot = Mock()
        self.scheduler = NotificationScheduler(self.bot)

    def test_scheduler_initialization(self):
        """Тест инициализации планировщика."""
        self.assertIsNotNone(self.scheduler.scheduler)
        self.assertIsNotNone(self.scheduler.bot)

    @patch('src.notifications.scheduler.AsyncIOScheduler')
    def test_start_scheduler(self, mock_scheduler_class):
        """Тест запуска планировщика."""
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        scheduler = NotificationScheduler(self.bot)
        scheduler.start()

        mock_scheduler.start.assert_called_once()

    @patch('src.notifications.scheduler.AsyncIOScheduler')
    def test_stop_scheduler(self, mock_scheduler_class):
        """Тест остановки планировщика."""
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        scheduler = NotificationScheduler(self.bot)
        scheduler.shutdown()

        mock_scheduler.shutdown.assert_called_once()

    def test_add_notification_job(self):
        """Тест добавления задачи уведомления."""
        user_id = 123
        notification_type = NotificationType.OVULATION_DAY
        run_date = datetime.now() + timedelta(days=1)

        with patch.object(self.scheduler.scheduler, 'add_job') as mock_add_job:
            self.scheduler.add_notification_job(
                user_id, notification_type, run_date
            )

            mock_add_job.assert_called_once()
            args, kwargs = mock_add_job.call_args

            # Проверяем параметры вызова
            self.assertEqual(kwargs['trigger'], 'date')
            self.assertEqual(kwargs['run_date'], run_date)
            self.assertIn(str(user_id), kwargs['id'])
            self.assertIn(notification_type.value, kwargs['id'])

    def test_remove_notification_job(self):
        """Тест удаления задачи уведомления."""
        user_id = 123
        notification_type = NotificationType.PERIOD_REMINDER

        with patch.object(self.scheduler.scheduler, 'remove_job') as mock_remove_job:
            self.scheduler.remove_notification_job(user_id, notification_type)

            mock_remove_job.assert_called_once()
            job_id = mock_remove_job.call_args[0][0]
            self.assertIn(str(user_id), job_id)
            self.assertIn(notification_type.value, job_id)

    def test_remove_user_jobs(self):
        """Тест удаления всех задач пользователя."""
        user_id = 123

        # Создаем моковые задачи
        job1 = Mock()
        job1.id = f"notification_{user_id}_OVULATION_DAY"
        job2 = Mock()
        job2.id = f"notification_{user_id}_PERIOD_REMINDER"
        job3 = Mock()
        job3.id = "notification_456_OVULATION_DAY"  # Другой пользователь

        with patch.object(self.scheduler.scheduler, 'get_jobs') as mock_get_jobs:
            with patch.object(self.scheduler.scheduler, 'remove_job') as mock_remove_job:
                mock_get_jobs.return_value = [job1, job2, job3]

                self.scheduler.remove_user_jobs(user_id)

                # Должны быть удалены только задачи пользователя 123
                self.assertEqual(mock_remove_job.call_count, 2)
                mock_remove_job.assert_any_call(job1.id)
                mock_remove_job.assert_any_call(job2.id)

    def test_get_user_jobs(self):
        """Тест получения задач пользователя."""
        user_id = 123

        job1 = Mock()
        job1.id = f"notification_{user_id}_OVULATION_DAY"
        job2 = Mock()
        job2.id = f"notification_{user_id}_PERIOD_REMINDER"
        job3 = Mock()
        job3.id = "notification_456_OVULATION_DAY"

        with patch.object(self.scheduler.scheduler, 'get_jobs') as mock_get_jobs:
            mock_get_jobs.return_value = [job1, job2, job3]

            result = self.scheduler.get_user_jobs(user_id)

            self.assertEqual(len(result), 2)
            self.assertIn(job1, result)
            self.assertIn(job2, result)
            self.assertNotIn(job3, result)


class TestNotificationSender(unittest.TestCase):
    """Тесты для функций отправки уведомлений."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.user_id = 1
        self.telegram_id = 12345
        self.notification_type = NotificationType.OVULATION_DAY

    @patch('src.notifications.sender.get_session')
    @patch('src.notifications.sender.get_user')
    @patch('src.notifications.sender.create_notification_log')
    def test_send_notification_success(self, mock_log, mock_get_user, mock_session):
        """Тест успешной отправки уведомления."""
        # Настройка моков
        mock_user = Mock(spec=User)
        mock_user.id = self.user_id
        mock_user.telegram_id = self.telegram_id
        mock_user.is_active = True
        mock_get_user.return_value = mock_user

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch('src.notifications.sender.bot') as mock_bot:
            mock_bot.send_message = AsyncMock()

            # Вызываем функцию
            asyncio.run(send_notification(
                self.user_id, self.notification_type
            ))

            # Проверяем вызовы
            mock_get_user.assert_called_once_with(mock_db, user_id=self.user_id)
            mock_bot.send_message.assert_called_once()

            # Проверяем параметры отправки
            args, kwargs = mock_bot.send_message.call_args
            self.assertEqual(args[0], self.telegram_id)
            self.assertIn('text', kwargs)

            # Проверяем создание лога
            mock_log.assert_called_once()

    @patch('src.notifications.sender.get_session')
    @patch('src.notifications.sender.get_user')
    def test_send_notification_user_not_found(self, mock_get_user, mock_session):
        """Тест отправки уведомления несуществующему пользователю."""
        mock_get_user.return_value = None
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch('src.notifications.sender.logger') as mock_logger:
            asyncio.run(send_notification(
                self.user_id, self.notification_type
            ))

            # Проверяем, что залогировалась ошибка
            mock_logger.error.assert_called_once()

    @patch('src.notifications.sender.get_session')
    @patch('src.notifications.sender.get_user')
    def test_send_notification_inactive_user(self, mock_get_user, mock_session):
        """Тест отправки уведомления неактивному пользователю."""
        mock_user = Mock(spec=User)
        mock_user.id = self.user_id
        mock_user.telegram_id = self.telegram_id
        mock_user.is_active = False
        mock_get_user.return_value = mock_user

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch('src.notifications.sender.logger') as mock_logger:
            asyncio.run(send_notification(
                self.user_id, self.notification_type
            ))

            # Проверяем, что залогировалась информация
            mock_logger.info.assert_called_once()

    @patch('src.notifications.sender.get_session')
    @patch('src.notifications.sender.get_user')
    @patch('src.notifications.sender.create_notification_log')
    @patch('src.notifications.sender.retry_send_notification')
    def test_send_notification_with_rate_limit(
        self, mock_retry, mock_log, mock_get_user, mock_session
    ):
        """Тест обработки rate limiting при отправке."""
        from telegram.error import RetryAfter

        mock_user = Mock(spec=User)
        mock_user.id = self.user_id
        mock_user.telegram_id = self.telegram_id
        mock_user.is_active = True
        mock_get_user.return_value = mock_user

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch('src.notifications.sender.bot') as mock_bot:
            # Симулируем rate limiting
            mock_bot.send_message = AsyncMock(
                side_effect=RetryAfter(retry_after=5)
            )

            asyncio.run(send_notification(
                self.user_id, self.notification_type
            ))

            # Проверяем, что вызвана функция повторной отправки
            mock_retry.assert_called_once()
            args = mock_retry.call_args[0]
            self.assertEqual(args[0], self.user_id)
            self.assertEqual(args[1], self.notification_type)
            self.assertEqual(args[2], 5)  # retry_after

    @patch('src.notifications.sender.get_session')
    @patch('src.notifications.sender.get_user')
    @patch('src.notifications.sender.update_user_active_status')
    def test_send_notification_user_blocked_bot(
        self, mock_update_status, mock_get_user, mock_session
    ):
        """Тест обработки случая, когда пользователь заблокировал бота."""
        from telegram.error import Forbidden

        mock_user = Mock(spec=User)
        mock_user.id = self.user_id
        mock_user.telegram_id = self.telegram_id
        mock_user.is_active = True
        mock_get_user.return_value = mock_user

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch('src.notifications.sender.bot') as mock_bot:
            mock_bot.send_message = AsyncMock(
                side_effect=Forbidden("Bot was blocked by the user")
            )

            asyncio.run(send_notification(
                self.user_id, self.notification_type
            ))

            # Проверяем, что пользователь деактивирован
            mock_update_status.assert_called_once_with(
                mock_db, self.user_id, False
            )


class TestNotificationRescheduling(unittest.TestCase):
    """Тесты для пересчета уведомлений при изменении параметров."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.user = Mock(spec=User)
        self.user.id = 1
        self.user.telegram_id = 12345
        self.user.timezone = 'Europe/Moscow'

        self.cycle = Mock(spec=Cycle)
        self.cycle.id = 1
        self.cycle.user_id = 1
        self.cycle.start_date = date(2025, 10, 1)
        self.cycle.cycle_length = 28
        self.cycle.period_length = 5
        self.cycle.is_current = True

        self.scheduler = Mock(spec=NotificationScheduler)

    @patch('src.notifications.scheduler_utils.get_notification_settings')
    @patch('src.notifications.scheduler_utils.get_all_notification_times')
    def test_reschedule_notifications_for_cycle(
        self, mock_get_times, mock_get_settings
    ):
        """Тест пересчета уведомлений для цикла."""
        # Настройка моков
        settings = []
        for notification_type in NotificationType:
            setting = Mock(spec=NotificationSettings)
            setting.notification_type = notification_type.value
            setting.is_enabled = True
            settings.append(setting)
        mock_get_settings.return_value = settings

        notification_times = {}
        for notification_type in NotificationType:
            notification_times[notification_type] = datetime.now() + timedelta(days=1)
        mock_get_times.return_value = notification_times

        # Вызываем функцию
        reschedule_notifications_for_cycle(
            self.user, self.cycle, self.scheduler
        )

        # Проверяем, что старые задачи удалены
        self.scheduler.remove_user_jobs.assert_called_once_with(self.user.id)

        # Проверяем, что новые задачи добавлены
        self.assertEqual(
            self.scheduler.add_notification_job.call_count,
            len(NotificationType)
        )

    @patch('src.notifications.scheduler_utils.get_notification_settings')
    def test_reschedule_with_disabled_notifications(self, mock_get_settings):
        """Тест, что отключенные уведомления не создаются."""
        # Создаем настройки с отключенными уведомлениями
        settings = []
        for i, notification_type in enumerate(NotificationType):
            setting = Mock(spec=NotificationSettings)
            setting.notification_type = notification_type.value
            setting.is_enabled = (i % 2 == 0)  # Каждое второе отключено
            settings.append(setting)
        mock_get_settings.return_value = settings

        with patch('src.notifications.scheduler_utils.get_all_notification_times') as mock_times:
            notification_times = {
                nt: datetime.now() + timedelta(days=1)
                for nt in NotificationType
            }
            mock_times.return_value = notification_times

            reschedule_notifications_for_cycle(
                self.user, self.cycle, self.scheduler
            )

            # Проверяем, что добавлены только включенные уведомления
            enabled_count = sum(1 for s in settings if s.is_enabled)
            self.assertEqual(
                self.scheduler.add_notification_job.call_count,
                enabled_count
            )


class TestSendTestNotification(unittest.TestCase):
    """Тесты для отправки тестовых уведомлений."""

    @patch('src.notifications.sender.get_session')
    @patch('src.notifications.sender.get_user')
    def test_send_test_notification(self, mock_get_user, mock_session):
        """Тест отправки тестового уведомления."""
        user_id = 1
        telegram_id = 12345
        notification_type = NotificationType.OVULATION_DAY

        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.telegram_id = telegram_id
        mock_user.is_active = True
        mock_get_user.return_value = mock_user

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch('src.notifications.sender.bot') as mock_bot:
            mock_bot.send_message = AsyncMock()

            asyncio.run(send_test_notification(user_id, notification_type))

            # Проверяем, что сообщение отправлено
            mock_bot.send_message.assert_called_once()
            args, kwargs = mock_bot.send_message.call_args
            self.assertEqual(args[0], telegram_id)
            self.assertIn('ТЕСТ', kwargs['text'])


class TestIntegrationNotifications(unittest.TestCase):
    """Интеграционные тесты для системы уведомлений."""

    @patch('src.notifications.scheduler.AsyncIOScheduler')
    @patch('src.notifications.sender.bot')
    @patch('src.database.crud.get_session')
    def test_full_notification_flow(self, mock_session, mock_bot, mock_scheduler_class):
        """Тест полного цикла работы с уведомлениями."""
        # Настройка данных
        user = Mock(spec=User)
        user.id = 1
        user.telegram_id = 12345
        user.timezone = 'Europe/Moscow'
        user.is_active = True

        cycle = Mock(spec=Cycle)
        cycle.id = 1
        cycle.user_id = 1
        cycle.start_date = date.today()
        cycle.cycle_length = 28
        cycle.period_length = 5
        cycle.is_current = True

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Создаем планировщик
        bot_mock = Mock()
        scheduler = NotificationScheduler(bot_mock)

        # Добавляем задачу
        run_date = datetime.now() + timedelta(seconds=1)
        notification_type = NotificationType.OVULATION_DAY

        with patch.object(scheduler.scheduler, 'add_job') as mock_add_job:
            scheduler.add_notification_job(user.id, notification_type, run_date)
            mock_add_job.assert_called_once()

        # Проверяем получение задач пользователя
        job_mock = Mock()
        job_mock.id = f"notification_{user.id}_{notification_type.value}"

        with patch.object(scheduler.scheduler, 'get_jobs') as mock_get_jobs:
            mock_get_jobs.return_value = [job_mock]
            jobs = scheduler.get_user_jobs(user.id)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].id, job_mock.id)


if __name__ == '__main__':
    unittest.main()