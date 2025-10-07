"""
CRUD operations for database models.
Provides functions for Create, Read, Update, Delete operations.
"""

from utils.logger import get_logger, log_database_operation
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.user import User
from models.cycle import Cycle
from models.notification_settings import NotificationSettings
from models.notification_log import NotificationLog
from database.session import db_session

# Set up logging
logger = get_logger(__name__)


# ============================================================================
# User CRUD Operations
# ============================================================================

def create_user(
    telegram_id: int,
    username: Optional[str] = None,
    timezone: str = 'Europe/Moscow',
    preferred_language: str = 'ru',
    session: Optional[Session] = None
) -> Optional[User]:
    """
    Create a new user in the database.

    Args:
        telegram_id: Telegram user ID
        username: Telegram username
        timezone: User's timezone (default: Europe/Moscow)
        preferred_language: User's preferred language (default: ru)
        session: Optional database session

    Returns:
        User: Created user object or None if error

    Raises:
        IntegrityError: If user with this telegram_id already exists
    """
    def _create(db: Session):
        try:
            # Check if user already exists
            existing_user = db.query(User).filter_by(telegram_id=telegram_id).first()
            if existing_user:
                logger.warning(f"User with telegram_id {telegram_id} already exists")
                db.expunge(existing_user)
                return existing_user

            user = User(
                telegram_id=telegram_id,
                username=username,
                timezone=timezone,
                preferred_language=preferred_language,
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Expunge the object from session to make it detached but usable
            db.expunge(user)

            logger.info(f"Created new user: telegram_id={telegram_id}, username={username}")
            return user

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating user: {str(e)}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating user: {str(e)}")
            return None

    if session:
        return _create(session)
    else:
        with db_session.get_session() as db:
            return _create(db)


def get_user(
    telegram_id: Optional[int] = None,
    user_id: Optional[int] = None,
    session: Optional[Session] = None
) -> Optional[User]:
    """
    Get user by telegram_id or user_id.

    Args:
        telegram_id: Telegram user ID
        user_id: Database user ID
        session: Optional database session

    Returns:
        User: User object or None if not found
    """
    def _get(db: Session):
        try:
            query = db.query(User)

            if telegram_id is not None:
                user = query.filter_by(telegram_id=telegram_id).first()
            elif user_id is not None:
                user = query.filter_by(id=user_id).first()
            else:
                logger.error("Either telegram_id or user_id must be provided")
                return None

            if user:
                # Expunge the object from session to make it detached but usable
                db.expunge(user)
                logger.debug(f"Found user: telegram_id={telegram_id}, user_id={user_id}")
            else:
                logger.debug(f"User not found: telegram_id={telegram_id}, user_id={user_id}")

            return user

        except SQLAlchemyError as e:
            logger.error(f"Database error getting user: {str(e)}")
            return None

    if session:
        return _get(session)
    else:
        with db_session.get_session() as db:
            return _get(db)


def update_user(
    telegram_id: int,
    updates: Dict[str, Any],
    session: Optional[Session] = None
) -> Optional[User]:
    """
    Update user information.

    Args:
        telegram_id: Telegram user ID
        updates: Dictionary with fields to update
        session: Optional database session

    Returns:
        User: Updated user object or None if error
    """
    def _update(db: Session):
        try:
            user = db.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                logger.error(f"User with telegram_id {telegram_id} not found")
                return None

            # Update allowed fields
            allowed_fields = {'username', 'timezone', 'preferred_language', 'is_active'}
            for field, value in updates.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)

            # Always update last_active_at
            user.last_active_at = datetime.utcnow()

            db.commit()
            db.refresh(user)
            db.expunge(user)

            logger.info(f"Updated user {telegram_id}: {updates}")
            return user

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating user: {str(e)}")
            return None

    if session:
        return _update(session)
    else:
        with db_session.get_session() as db:
            return _update(db)


def update_user_active_status(
    db: Session,
    user_id: int,
    is_active: bool
) -> Optional[User]:
    """
    Update user's active status.

    Used when a user blocks/unblocks the bot.

    Args:
        db: Database session
        user_id: User ID in database (not telegram_id)
        is_active: New active status

    Returns:
        User: Updated user object or None if error
    """
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            logger.error(f"User with id {user_id} not found")
            return None

        user.is_active = is_active
        user.last_active_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        logger.info(f"Updated active status for user {user_id}: is_active={is_active}")
        return user

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating user active status: {str(e)}")
        return None


def delete_user(
    telegram_id: int,
    session: Optional[Session] = None
) -> bool:
    """
    Delete user and all related data (cascading delete).

    Args:
        telegram_id: Telegram user ID
        session: Optional database session

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    def _delete(db: Session):
        try:
            user = db.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                logger.error(f"User with telegram_id {telegram_id} not found")
                return False

            db.delete(user)
            db.commit()

            logger.info(f"Deleted user with telegram_id {telegram_id}")
            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error deleting user: {str(e)}")
            return False

    if session:
        return _delete(session)
    else:
        with db_session.get_session() as db:
            return _delete(db)


def get_all_active_users(session: Optional[Session] = None) -> List[User]:
    """
    Get all active users.

    Args:
        session: Optional database session

    Returns:
        List[User]: List of active users
    """
    def _get_all(db: Session):
        try:
            users = db.query(User).filter_by(is_active=True).all()
            # Expunge all objects from session
            for user in users:
                db.expunge(user)
            logger.debug(f"Found {len(users)} active users")
            return users
        except SQLAlchemyError as e:
            logger.error(f"Database error getting active users: {str(e)}")
            return []

    if session:
        return _get_all(session)
    else:
        with db_session.get_session() as db:
            return _get_all(db)


# ============================================================================
# Cycle CRUD Operations
# ============================================================================

def create_cycle(
    user_id: int,
    start_date: date,
    cycle_length: int,
    period_length: int,
    is_current: bool = True,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Optional[Cycle]:
    """
    Create a new cycle for a user.

    Args:
        user_id: Database user ID
        start_date: Start date of the cycle
        cycle_length: Length of the cycle in days (21-40)
        period_length: Length of period in days (1-10)
        is_current: Whether this is the current active cycle
        notes: Optional notes
        session: Optional database session

    Returns:
        Cycle: Created cycle object or None if error

    Raises:
        ValueError: If cycle parameters are invalid
    """
    def _create(db: Session):
        try:
            # Validate parameters
            if not (21 <= cycle_length <= 40):
                raise ValueError(f"Cycle length must be between 21 and 40 days, got {cycle_length}")
            if not (1 <= period_length <= 10):
                raise ValueError(f"Period length must be between 1 and 10 days, got {period_length}")

            # If marking as current, deactivate other cycles
            if is_current:
                db.query(Cycle).filter_by(
                    user_id=user_id,
                    is_current=True
                ).update({'is_current': False})

            cycle = Cycle(
                user_id=user_id,
                start_date=start_date,
                cycle_length=cycle_length,
                period_length=period_length,
                is_current=is_current,
                notes=notes,
                created_at=datetime.utcnow()
            )
            db.add(cycle)
            db.commit()
            db.refresh(cycle)
            db.expunge(cycle)

            logger.info(f"Created new cycle for user {user_id}, start_date={start_date}")
            return cycle

        except ValueError as e:
            logger.error(f"Validation error creating cycle: {str(e)}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating cycle: {str(e)}")
            return None

    if session:
        return _create(session)
    else:
        with db_session.get_session() as db:
            return _create(db)


def get_current_cycle(
    user_id: int,
    session: Optional[Session] = None
) -> Optional[Cycle]:
    """
    Get the current active cycle for a user.

    Args:
        user_id: Database user ID
        session: Optional database session

    Returns:
        Cycle: Current cycle object or None if not found
    """
    def _get(db: Session):
        try:
            cycle = db.query(Cycle).filter_by(
                user_id=user_id,
                is_current=True
            ).first()

            if cycle:
                db.expunge(cycle)
                logger.debug(f"Found current cycle for user {user_id}")
            else:
                logger.debug(f"No current cycle found for user {user_id}")

            return cycle

        except SQLAlchemyError as e:
            logger.error(f"Database error getting current cycle: {str(e)}")
            return None

    if session:
        return _get(session)
    else:
        with db_session.get_session() as db:
            return _get(db)


def get_cycle_by_id(
    session: Session,
    cycle_id: int
) -> Optional[Cycle]:
    """
    Get a cycle by its ID.

    Args:
        session: Database session
        cycle_id: ID of the cycle

    Returns:
        Optional[Cycle]: Cycle object or None if not found
    """
    try:
        cycle = session.query(Cycle).filter_by(id=cycle_id).first()
        if cycle:
            session.expunge(cycle)
            logger.debug(f"Found cycle with id {cycle_id}")
        else:
            logger.debug(f"No cycle found with id {cycle_id}")
        return cycle
    except SQLAlchemyError as e:
        logger.error(f"Database error getting cycle by id: {str(e)}")
        return None


def get_user_cycles(
    user_id: int,
    limit: Optional[int] = None,
    session: Optional[Session] = None
) -> List[Cycle]:
    """
    Get all cycles for a user, ordered by start date descending.

    Args:
        user_id: Database user ID
        limit: Maximum number of cycles to return
        session: Optional database session

    Returns:
        List[Cycle]: List of cycles
    """
    def _get_all(db: Session):
        try:
            query = db.query(Cycle).filter_by(user_id=user_id)
            query = query.order_by(Cycle.start_date.desc())

            if limit:
                query = query.limit(limit)

            cycles = query.all()
            # Expunge all objects from session
            for cycle in cycles:
                db.expunge(cycle)
            logger.debug(f"Found {len(cycles)} cycles for user {user_id}")
            return cycles

        except SQLAlchemyError as e:
            logger.error(f"Database error getting user cycles: {str(e)}")
            return []

    if session:
        return _get_all(session)
    else:
        with db_session.get_session() as db:
            return _get_all(db)


def update_cycle(
    cycle_id: int,
    updates: Dict[str, Any],
    session: Optional[Session] = None
) -> Optional[Cycle]:
    """
    Update cycle information.

    Args:
        cycle_id: Database cycle ID
        updates: Dictionary with fields to update
        session: Optional database session

    Returns:
        Cycle: Updated cycle object or None if error

    Raises:
        ValueError: If cycle parameters are invalid
    """
    def _update(db: Session):
        try:
            cycle = db.query(Cycle).filter_by(id=cycle_id).first()
            if not cycle:
                logger.error(f"Cycle with id {cycle_id} not found")
                return None

            # Validate parameters if they're being updated
            if 'cycle_length' in updates:
                if not (21 <= updates['cycle_length'] <= 40):
                    raise ValueError(f"Cycle length must be between 21 and 40 days")

            if 'period_length' in updates:
                if not (1 <= updates['period_length'] <= 10):
                    raise ValueError(f"Period length must be between 1 and 10 days")

            # If setting as current, deactivate other cycles for this user
            if updates.get('is_current') == True:
                db.query(Cycle).filter(
                    Cycle.user_id == cycle.user_id,
                    Cycle.id != cycle_id
                ).update({'is_current': False})

            # Update allowed fields
            allowed_fields = {'start_date', 'cycle_length', 'period_length', 'is_current', 'notes'}
            for field, value in updates.items():
                if field in allowed_fields and hasattr(cycle, field):
                    setattr(cycle, field, value)

            cycle.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(cycle)
            db.expunge(cycle)

            logger.info(f"Updated cycle {cycle_id}: {updates}")
            return cycle

        except ValueError as e:
            logger.error(f"Validation error updating cycle: {str(e)}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating cycle: {str(e)}")
            return None

    if session:
        return _update(session)
    else:
        with db_session.get_session() as db:
            return _update(db)


def update_cycle_status(
    session: Session,
    cycle_id: int,
    is_current: bool
) -> Optional[Cycle]:
    """
    Update only the is_current status of a cycle.

    Args:
        session: Database session (required)
        cycle_id: Database cycle ID
        is_current: New status for the cycle

    Returns:
        Cycle: Updated cycle object or None if error
    """
    return update_cycle(cycle_id, {'is_current': is_current}, session=session)


def delete_cycle(
    cycle_id: int,
    session: Optional[Session] = None
) -> bool:
    """
    Delete a cycle.

    Args:
        cycle_id: Database cycle ID
        session: Optional database session

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    def _delete(db: Session):
        try:
            cycle = db.query(Cycle).filter_by(id=cycle_id).first()
            if not cycle:
                logger.error(f"Cycle with id {cycle_id} not found")
                return False

            db.delete(cycle)
            db.commit()

            logger.info(f"Deleted cycle with id {cycle_id}")
            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error deleting cycle: {str(e)}")
            return False

    if session:
        return _delete(session)
    else:
        with db_session.get_session() as db:
            return _delete(db)


# ============================================================================
# Notification Settings CRUD Operations
# ============================================================================

def create_notification_settings(
    user_id: int,
    notification_type: str,
    is_enabled: bool = True,
    time_offset: int = 0,
    session: Optional[Session] = None
) -> Optional[NotificationSettings]:
    """
    Create notification settings for a user.

    Args:
        user_id: Database user ID
        notification_type: Type of notification
        is_enabled: Whether notification is enabled
        time_offset: Time offset in minutes
        session: Optional database session

    Returns:
        NotificationSettings: Created settings object or None if error
    """
    def _create(db: Session):
        try:
            # Check if settings already exist for this type
            existing = db.query(NotificationSettings).filter_by(
                user_id=user_id,
                notification_type=notification_type
            ).first()

            if existing:
                logger.warning(f"Notification settings already exist for user {user_id}, type {notification_type}")
                return existing

            settings = NotificationSettings(
                user_id=user_id,
                notification_type=notification_type,
                is_enabled=is_enabled,
                time_offset=time_offset,
                created_at=datetime.utcnow()
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
            db.expunge(settings)

            logger.info(f"Created notification settings for user {user_id}, type={notification_type}")
            return settings

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating notification settings: {str(e)}")
            return None

    if session:
        return _create(session)
    else:
        with db_session.get_session() as db:
            return _create(db)


def get_user_notification_settings(
    user_id: int,
    session: Optional[Session] = None
) -> List[NotificationSettings]:
    """
    Get all notification settings for a user.

    Args:
        user_id: Database user ID
        session: Optional database session

    Returns:
        List[NotificationSettings]: List of notification settings
    """
    def _get_all(db: Session):
        try:
            settings = db.query(NotificationSettings).filter_by(user_id=user_id).all()
            for s in settings:
                db.expunge(s)
            logger.debug(f"Found {len(settings)} notification settings for user {user_id}")
            return settings
        except SQLAlchemyError as e:
            logger.error(f"Database error getting notification settings: {str(e)}")
            return []

    if session:
        return _get_all(session)
    else:
        with db_session.get_session() as db:
            return _get_all(db)


def update_notification_settings(
    settings_id: int,
    updates: Dict[str, Any],
    session: Optional[Session] = None
) -> Optional[NotificationSettings]:
    """
    Update notification settings.

    Args:
        settings_id: Database settings ID
        updates: Dictionary with fields to update
        session: Optional database session

    Returns:
        NotificationSettings: Updated settings object or None if error
    """
    def _update(db: Session):
        try:
            settings = db.query(NotificationSettings).filter_by(id=settings_id).first()
            if not settings:
                logger.error(f"Notification settings with id {settings_id} not found")
                return None

            # Update allowed fields
            allowed_fields = {'is_enabled', 'time_offset'}
            for field, value in updates.items():
                if field in allowed_fields and hasattr(settings, field):
                    setattr(settings, field, value)

            settings.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(settings)
            db.expunge(settings)

            logger.info(f"Updated notification settings {settings_id}: {updates}")
            return settings

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating notification settings: {str(e)}")
            return None

    if session:
        return _update(session)
    else:
        with db_session.get_session() as db:
            return _update(db)


def update_notification_setting(
    user_id: int,
    notification_type: str,
    is_enabled: bool,
    session: Optional[Session] = None
) -> Optional[NotificationSettings]:
    """
    Update or create notification setting for a specific user and type.

    Args:
        user_id: Database user ID
        notification_type: Type of notification
        is_enabled: Whether notification is enabled
        session: Optional database session

    Returns:
        NotificationSettings: Updated/created settings object or None if error
    """
    def _update_or_create(db: Session):
        try:
            # Try to find existing setting
            settings = db.query(NotificationSettings).filter_by(
                user_id=user_id,
                notification_type=notification_type
            ).first()

            if settings:
                # Update existing
                settings.is_enabled = is_enabled
                settings.updated_at = datetime.utcnow()
                logger.info(f"Updated notification setting for user {user_id}, type={notification_type}: is_enabled={is_enabled}")
            else:
                # Create new
                settings = NotificationSettings(
                    user_id=user_id,
                    notification_type=notification_type,
                    is_enabled=is_enabled,
                    time_offset=0,
                    created_at=datetime.utcnow()
                )
                db.add(settings)
                logger.info(f"Created notification setting for user {user_id}, type={notification_type}: is_enabled={is_enabled}")

            db.commit()
            db.refresh(settings)
            db.expunge(settings)
            return settings

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating/creating notification setting: {str(e)}")
            return None

    if session:
        return _update_or_create(session)
    else:
        with db_session.get_session() as db:
            return _update_or_create(db)


# ============================================================================
# Notification Log CRUD Operations
# ============================================================================

def create_notification_log(
    user_id: int,
    notification_type: str,
    status: str = 'sent',
    error_message: Optional[str] = None,
    session: Optional[Session] = None
) -> Optional[NotificationLog]:
    """
    Create a notification log entry.

    Args:
        user_id: Database user ID
        notification_type: Type of notification
        status: Status of notification ('sent', 'failed', 'pending')
        error_message: Error message if failed
        session: Optional database session

    Returns:
        NotificationLog: Created log entry or None if error
    """
    def _create(db: Session):
        try:
            log = NotificationLog(
                user_id=user_id,
                notification_type=notification_type,
                status=status,
                error_message=error_message,
                sent_at=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            db.expunge(log)

            logger.info(f"Created notification log for user {user_id}, type={notification_type}")
            return log

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating notification log: {str(e)}")
            return None

    if session:
        return _create(session)
    else:
        with db_session.get_session() as db:
            return _create(db)


def get_user_notification_logs(
    user_id: int,
    limit: Optional[int] = None,
    notification_type: Optional[str] = None,
    session: Optional[Session] = None
) -> List[NotificationLog]:
    """
    Get notification logs for a user.

    Args:
        user_id: Database user ID
        limit: Maximum number of logs to return
        notification_type: Filter by notification type
        session: Optional database session

    Returns:
        List[NotificationLog]: List of notification logs
    """
    def _get_logs(db: Session):
        try:
            query = db.query(NotificationLog).filter_by(user_id=user_id)

            if notification_type:
                query = query.filter_by(notification_type=notification_type)

            query = query.order_by(NotificationLog.sent_at.desc())

            if limit:
                query = query.limit(limit)

            logs = query.all()
            for log in logs:
                db.expunge(log)
            logger.debug(f"Found {len(logs)} notification logs for user {user_id}")
            return logs

        except SQLAlchemyError as e:
            logger.error(f"Database error getting notification logs: {str(e)}")
            return []

    if session:
        return _get_logs(session)
    else:
        with db_session.get_session() as db:
            return _get_logs(db)


# Alias for compatibility
get_notification_logs = get_user_notification_logs


# ============================================================================
# Helper Functions
# ============================================================================

def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    timezone: str = 'Europe/Moscow',
    session: Optional[Session] = None
) -> Optional[User]:
    """
    Get existing user or create new one.

    Args:
        telegram_id: Telegram user ID
        username: Telegram username
        timezone: User's timezone
        session: Optional database session

    Returns:
        User: User object or None if error
    """
    def _get_or_create(db: Session):
        # Import User here to avoid circular imports
        from models.user import User
        # Get user directly in this session
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            # Update last activity
            user.last_active_at = datetime.utcnow()
            user.increment_command_count()
            db.commit()
            user_id = user.id
            telegram_id_found = user.telegram_id
            db.expunge(user)
            logger.debug(f"Found existing user: id={user_id}, telegram_id={telegram_id_found}")
            return user

        # Create new user if not exists
        return create_user(
            telegram_id=telegram_id,
            username=username,
            timezone=timezone,
            session=db
        )

    if session:
        return _get_or_create(session)
    else:
        with db_session.get_session() as db:
            return _get_or_create(db)


def deactivate_user(
    telegram_id: int,
    session: Optional[Session] = None
) -> bool:
    """
    Deactivate a user (e.g., when bot is blocked).

    Args:
        telegram_id: Telegram user ID
        session: Optional database session

    Returns:
        bool: True if deactivated successfully
    """
    return update_user(
        telegram_id=telegram_id,
        updates={'is_active': False},
        session=session
    ) is not None


def activate_user(
    telegram_id: int,
    session: Optional[Session] = None
) -> bool:
    """
    Activate a user.

    Args:
        telegram_id: Telegram user ID
        session: Optional database session

    Returns:
        bool: True if activated successfully
    """
    return update_user(
        telegram_id=telegram_id,
        updates={'is_active': True},
        session=session
    ) is not None