"""
Модуль для управления планировщиком уведомлений с использованием APScheduler.

Этот модуль обеспечивает:
- Инициализацию планировщика с персистентным хранилищем в БД
- Добавление и удаление задач уведомлений
- Восстановление задач после перезапуска
- Интеграцию с системой уведомлений бота
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    EVENT_JOB_ADDED,
    EVENT_JOB_REMOVED,
    JobExecutionEvent
)

from database.config import DATABASE_URL
from database.session import Session
from database.crud import get_user, get_all_active_users
from models.notification_settings import NotificationSettings
from notifications.types import NotificationType
from utils.logger import get_logger, log_notification_event, log_error

logger = get_logger(__name__)


class NotificationScheduler:
    """
    Класс для управления планировщиком уведомлений.

    Использует APScheduler с SQLAlchemy JobStore для персистентного хранения задач.
    """

    def __init__(self, bot_application=None):
        """
        Инициализация планировщика.

        Args:
            bot_application: Экземпляр Application из python-telegram-bot
        """
        self.bot_application = bot_application
        self.scheduler = None
        self._is_running = False

    def initialize(self) -> None:
        """
        Инициализация планировщика с настройками и хранилищем.
        """
        # Настройка хранилища задач в БД
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=DATABASE_URL,
                tablename='apscheduler_jobs',
                engine_options={
                    'pool_pre_ping': True,
                    'pool_size': 5,
                    'max_overflow': 10
                }
            )
        }

        # Настройка исполнителей задач
        executors = {
            'default': AsyncIOExecutor()
        }

        # Настройки планировщика
        job_defaults = {
            'coalesce': True,  # Объединять пропущенные задачи
            'max_instances': 3,  # Максимум экземпляров одной задачи
            'misfire_grace_time': 30  # Время допуска опоздания (секунды)
        }

        # Создание планировщика
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'  # Используем UTC для хранения, конвертируем при отправке
        )

        # Добавление обработчиков событий
        self.scheduler.add_listener(
            self._handle_job_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )
        self.scheduler.add_listener(
            self._handle_job_added,
            EVENT_JOB_ADDED
        )
        self.scheduler.add_listener(
            self._handle_job_removed,
            EVENT_JOB_REMOVED
        )

        logger.info("Планировщик уведомлений инициализирован")

    async def start(self) -> None:
        """
        Запуск планировщика и восстановление задач.
        """
        if self._is_running:
            logger.warning("Планировщик уже запущен")
            return

        if not self.scheduler:
            self.initialize()

        self.scheduler.start()
        self._is_running = True
        logger.info("Планировщик уведомлений запущен")

        # Восстановление задач после перезапуска
        await self.restore_jobs()

    async def stop(self) -> None:
        """
        Остановка планировщика.
        """
        if not self._is_running:
            return

        self.scheduler.shutdown(wait=True)
        self._is_running = False
        logger.info("Планировщик уведомлений остановлен")

    async def add_notification_job(
        self,
        user_id: int,
        notification_type: NotificationType,
        send_at: datetime,
        **kwargs
    ) -> Optional[str]:
        """
        Добавление задачи на отправку уведомления.

        Args:
            user_id: ID пользователя
            notification_type: Тип уведомления
            send_at: Время отправки уведомления
            **kwargs: Дополнительные параметры для задачи

        Returns:
            ID созданной задачи или None при ошибке
        """
        # Проверка что время в будущем
        now = datetime.now(timezone.utc)
        if send_at <= now:
            logger.warning(
                f"Попытка создать задачу в прошлом: user_id={user_id}, "
                f"type={notification_type.value}, send_at={send_at}"
            )
            return None

        # Создание уникального ID задачи
        job_id = f"notification_{user_id}_{notification_type.value}_{send_at.timestamp()}"

        try:
            # Импортируем функцию отправки здесь чтобы избежать циклического импорта
            from notifications.sender import send_notification_async

            # Добавление задачи в планировщик
            self.scheduler.add_job(
                send_notification_async,
                'date',
                run_date=send_at,
                id=job_id,
                args=[user_id, notification_type],
                kwargs={'bot_application': self.bot_application},
                replace_existing=True,  # Заменять существующую задачу с тем же ID
                **kwargs
            )

            logger.info(
                f"Добавлена задача уведомления: id={job_id}, "
                f"user_id={user_id}, type={notification_type.value}, "
                f"send_at={send_at}"
            )
            return job_id

        except Exception as e:
            logger.error(
                f"Ошибка при добавлении задачи: user_id={user_id}, "
                f"type={notification_type.value}, error={str(e)}"
            )
            return None

    async def remove_notification_job(self, job_id: str) -> bool:
        """
        Удаление задачи уведомления.

        Args:
            job_id: ID задачи для удаления

        Returns:
            True если задача удалена успешно, False иначе
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Задача удалена: id={job_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении задачи {job_id}: {str(e)}")
            return False

    async def remove_user_jobs(self, user_id: int) -> int:
        """
        Удаление всех задач пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Количество удаленных задач
        """
        removed_count = 0
        jobs = self.scheduler.get_jobs()

        for job in jobs:
            if job.id.startswith(f"notification_{user_id}_"):
                if await self.remove_notification_job(job.id):
                    removed_count += 1

        logger.info(f"Удалено {removed_count} задач для пользователя {user_id}")
        return removed_count

    async def update_notification_job(
        self,
        job_id: str,
        new_send_at: datetime
    ) -> bool:
        """
        Обновление времени отправки задачи.

        Args:
            job_id: ID задачи
            new_send_at: Новое время отправки

        Returns:
            True если задача обновлена успешно, False иначе
        """
        try:
            self.scheduler.modify_job(
                job_id,
                run_date=new_send_at
            )
            logger.info(f"Задача обновлена: id={job_id}, new_time={new_send_at}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении задачи {job_id}: {str(e)}")
            return False

    async def get_user_jobs(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение списка задач пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список словарей с информацией о задачах
        """
        user_jobs = []
        jobs = self.scheduler.get_jobs()

        for job in jobs:
            if job.id.startswith(f"notification_{user_id}_"):
                # Парсинг ID задачи
                parts = job.id.split('_')
                if len(parts) >= 4:
                    notification_type = parts[2]
                    user_jobs.append({
                        'job_id': job.id,
                        'notification_type': notification_type,
                        'send_at': job.next_run_time,
                        'state': job.pending
                    })

        return user_jobs

    async def restore_jobs(self) -> int:
        """
        Восстановление задач после перезапуска бота.

        Эта функция проверяет настройки уведомлений всех активных пользователей
        и пересоздает задачи если необходимо.

        Returns:
            Количество восстановленных задач
        """
        logger.info("Начало восстановления задач уведомлений...")
        restored_count = 0

        with Session() as session:
            # Получаем всех активных пользователей
            active_users = get_all_active_users(session)

            for user in active_users:
                if not user.cycles:
                    continue

                # Получаем текущий цикл
                current_cycle = next(
                    (c for c in user.cycles if c.is_current),
                    None
                )

                if not current_cycle:
                    continue

                # Получаем настройки уведомлений пользователя
                settings = session.query(NotificationSettings).filter_by(
                    user_id=user.id,
                    is_enabled=True
                ).all()

                if not settings:
                    continue

                # Импортируем функцию расчета времени
                from notifications.scheduler_utils import get_all_notification_times

                # Рассчитываем времена уведомлений
                notification_times = get_all_notification_times(
                    current_cycle,
                    user.timezone
                )

                # Создаем задачи для включенных уведомлений
                for setting in settings:
                    notification_type = NotificationType(setting.notification_type)

                    if notification_type in notification_times:
                        send_at = notification_times[notification_type]

                        # Проверяем что время в будущем
                        if send_at > datetime.now(timezone.utc):
                            job_id = await self.add_notification_job(
                                user.id,
                                notification_type,
                                send_at
                            )
                            if job_id:
                                restored_count += 1

        logger.info(f"Восстановлено {restored_count} задач уведомлений")
        return restored_count

    def get_jobs_stats(self) -> Dict[str, Any]:
        """
        Получение статистики по задачам.

        Returns:
            Словарь со статистикой
        """
        jobs = self.scheduler.get_jobs()

        # Подсчет задач по типам
        type_counts = {}
        for job in jobs:
            if job.id.startswith("notification_"):
                parts = job.id.split('_')
                if len(parts) >= 3:
                    notification_type = parts[2]
                    type_counts[notification_type] = type_counts.get(notification_type, 0) + 1

        return {
            'total_jobs': len(jobs),
            'pending_jobs': sum(1 for job in jobs if job.pending),
            'jobs_by_type': type_counts,
            'is_running': self._is_running
        }

    # Обработчики событий планировщика

    def _handle_job_event(self, event: JobExecutionEvent) -> None:
        """
        Обработчик событий выполнения задач.

        Args:
            event: Событие выполнения задачи
        """
        if event.code == EVENT_JOB_EXECUTED:
            logger.debug(f"Задача выполнена успешно: {event.job_id}")
        elif event.code == EVENT_JOB_ERROR:
            logger.error(
                f"Ошибка при выполнении задачи {event.job_id}: "
                f"{event.exception}"
            )
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"Задача пропущена: {event.job_id}")

    def _handle_job_added(self, event) -> None:
        """
        Обработчик добавления задачи.

        Args:
            event: Событие добавления задачи
        """
        logger.debug(f"Задача добавлена в планировщик: {event.job_id}")

    def _handle_job_removed(self, event) -> None:
        """
        Обработчик удаления задачи.

        Args:
            event: Событие удаления задачи
        """
        logger.debug(f"Задача удалена из планировщика: {event.job_id}")


# Глобальный экземпляр планировщика
notification_scheduler = NotificationScheduler()


async def init_scheduler(bot_application) -> None:
    """
    Инициализация и запуск планировщика.

    Args:
        bot_application: Экземпляр Application из python-telegram-bot
    """
    notification_scheduler.bot_application = bot_application
    notification_scheduler.initialize()
    await notification_scheduler.start()


async def shutdown_scheduler() -> None:
    """
    Остановка планировщика.
    """
    await notification_scheduler.stop()


# Вспомогательные функции для работы с планировщиком

async def schedule_cycle_notifications(user_id: int, cycle_id: int) -> int:
    """
    Создание всех задач уведомлений для цикла пользователя.

    Args:
        user_id: ID пользователя
        cycle_id: ID цикла

    Returns:
        Количество созданных задач
    """
    from database.crud import get_cycle_by_id
    from notifications.scheduler_utils import get_all_notification_times

    created_count = 0

    with Session() as session:
        # Получаем цикл
        cycle = get_cycle_by_id(session, cycle_id)
        if not cycle:
            logger.error(f"Цикл {cycle_id} не найден")
            return 0

        # Получаем пользователя
        user = get_user(session, telegram_id=user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return 0

        # Получаем настройки уведомлений
        settings = session.query(NotificationSettings).filter_by(
            user_id=user.id,
            is_enabled=True
        ).all()

        if not settings:
            logger.info(f"У пользователя {user_id} нет включенных уведомлений")
            return 0

        # Рассчитываем времена уведомлений
        notification_times = get_all_notification_times(
            cycle,
            user.timezone
        )

        # Создаем задачи
        for setting in settings:
            notification_type = NotificationType(setting.notification_type)

            if notification_type in notification_times:
                send_at = notification_times[notification_type]

                # Проверяем что время в будущем
                if send_at > datetime.now(timezone.utc):
                    job_id = await notification_scheduler.add_notification_job(
                        user.id,
                        notification_type,
                        send_at
                    )
                    if job_id:
                        created_count += 1

    logger.info(
        f"Создано {created_count} задач уведомлений для пользователя {user_id}, "
        f"цикл {cycle_id}"
    )
    return created_count


async def reschedule_user_notifications(user_id: int) -> int:
    """
    Пересоздание всех задач уведомлений пользователя.

    Используется при изменении параметров цикла.

    Args:
        user_id: ID пользователя

    Returns:
        Количество пересозданных задач
    """
    # Удаляем старые задачи
    removed = await notification_scheduler.remove_user_jobs(user_id)
    logger.info(f"Удалено {removed} старых задач для пользователя {user_id}")

    # Создаем новые задачи
    with Session() as session:
        user = get_user(session, telegram_id=user_id)
        if not user or not user.cycles:
            return 0

        current_cycle = next(
            (c for c in user.cycles if c.is_current),
            None
        )

        if not current_cycle:
            return 0

        created = await schedule_cycle_notifications(user.id, current_cycle.id)

    logger.info(f"Создано {created} новых задач для пользователя {user_id}")
    return created