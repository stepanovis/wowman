"""
Integration tests for database operations.

Tests all CRUD operations for User, Cycle, NotificationSettings, and NotificationLog models.
Uses SQLite in-memory database for isolated testing.
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import models and database utilities
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.base import Base
from src.models.user import User
from src.models.cycle import Cycle
from src.models.notification_settings import NotificationSettings
from src.models.notification_log import NotificationLog
from src.database.crud import (
    create_user, get_user, update_user, delete_user,
    get_all_active_users, update_user_active_status,
    create_cycle, get_current_cycle, get_cycle_by_id, get_user_cycles,
    update_cycle, delete_cycle, update_cycle_status,
    create_notification_settings, get_user_notification_settings,
    update_notification_settings, update_notification_setting,
    create_notification_log, get_user_notification_logs,
    get_or_create_user, deactivate_user, activate_user
)
from src.notifications.types import NotificationType


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    # Use SQLite in-memory database for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create session
    session = TestingSessionLocal()

    yield session

    # Clean up
    session.close()
    engine.dispose()


class TestUserCRUD:
    """Test User model CRUD operations."""

    def test_create_user(self, test_db: Session):
        """Test creating a new user."""
        user = create_user(
            telegram_id=12345,
            username="test_user",
            timezone="Europe/Moscow",
            session=test_db
        )

        assert user is not None
        assert user.telegram_id == 12345
        assert user.username == "test_user"
        assert user.timezone == "Europe/Moscow"
        assert user.is_active is True
        assert user.created_at is not None

    def test_get_user_by_id(self, test_db: Session):
        """Test getting a user by ID."""
        # Create user
        created_user = create_user(telegram_id=12345, username="test_user", session=test_db)

        # Get user by ID
        user = get_user(user_id=created_user.id, session=test_db)

        assert user is not None
        assert user.id == created_user.id
        assert user.telegram_id == 12345

    def test_get_user_by_telegram_id(self, test_db: Session):
        """Test getting a user by Telegram ID."""
        # Create user
        create_user(telegram_id=12345, username="test_user", session=test_db)

        # Get user by Telegram ID
        user = get_user(telegram_id=12345, session=test_db)

        assert user is not None
        assert user.telegram_id == 12345
        assert user.username == "test_user"

    def test_update_user(self, test_db: Session):
        """Test updating user data."""
        # Create user
        user = create_user(telegram_id=12345, username="test_user", session=test_db)

        # Update user
        updated_user = update_user(
            telegram_id=12345,
            updates={
                "username": "updated_user",
                "timezone": "America/New_York"
            },
            session=test_db
        )

        assert updated_user is not None
        assert updated_user.username == "updated_user"
        assert updated_user.timezone == "America/New_York"
        assert updated_user.telegram_id == 12345  # Should not change

    def test_update_user_active_status(self, test_db: Session):
        """Test updating user active status."""
        # Create user
        user = create_user(telegram_id=12345, username="test_user", session=test_db)
        assert user.is_active is True

        # Deactivate user
        updated_user = update_user_active_status(test_db, user.id, False)

        assert updated_user is not None
        assert updated_user.is_active is False

        # Reactivate user
        updated_user = update_user_active_status(test_db, user.id, True)
        assert updated_user.is_active is True

    def test_delete_user(self, test_db: Session):
        """Test deleting a user."""
        # Create user
        user = create_user(telegram_id=12345, username="test_user", session=test_db)
        user_id = user.id

        # Delete user
        success = delete_user(telegram_id=12345, session=test_db)
        assert success is True

        # Verify user is deleted
        deleted_user = get_user(user_id=user_id, session=test_db)
        assert deleted_user is None

    def test_get_all_active_users(self, test_db: Session):
        """Test getting all active users."""
        # Create multiple users
        create_user(telegram_id=12345, username="user1", session=test_db)
        create_user(telegram_id=67890, username="user2", session=test_db)
        create_user(telegram_id=11111, username="user3", session=test_db)

        # Get all users
        users = get_all_active_users(session=test_db)

        assert len(users) == 3
        telegram_ids = [user.telegram_id for user in users]
        assert 12345 in telegram_ids
        assert 67890 in telegram_ids
        assert 11111 in telegram_ids

    def test_duplicate_telegram_id(self, test_db: Session):
        """Test that duplicate Telegram IDs are not allowed."""
        # Create first user
        create_user(telegram_id=12345, username="user1", session=test_db)

        # Try to create another user with same Telegram ID
        duplicate_user = create_user(telegram_id=12345, username="user2", session=test_db)

        # Should return the existing user without updating it
        assert duplicate_user is not None
        assert duplicate_user.username == "user1"  # Original username is retained

    def test_get_or_create_user(self, test_db: Session):
        """Test get_or_create_user function."""
        # First call should create user
        user = get_or_create_user(
            telegram_id=12345,
            username="test_user",
            session=test_db
        )

        assert user is not None
        assert user.telegram_id == 12345

        # Second call should get existing user
        user2 = get_or_create_user(
            telegram_id=12345,
            username="new_name",
            session=test_db
        )

        assert user2 is not None
        assert user2.id == user.id
        # Username should NOT be updated (existing user is returned)
        assert user2.username == "test_user"

    def test_deactivate_activate_user(self, test_db: Session):
        """Test deactivate and activate user functions."""
        # Create user
        user = create_user(telegram_id=12345, username="test_user", session=test_db)

        # Deactivate user
        deactivated = deactivate_user(telegram_id=12345, session=test_db)
        assert deactivated is True

        # Check user is deactivated
        user = get_user(telegram_id=12345, session=test_db)
        assert user.is_active is False

        # Activate user
        activated = activate_user(telegram_id=12345, session=test_db)
        assert activated is True

        # Check user is activated
        user = get_user(telegram_id=12345, session=test_db)
        assert user.is_active is True


class TestCycleCRUD:
    """Test Cycle model CRUD operations."""

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user for cycle tests."""
        return create_user(telegram_id=12345, username="test_user", session=test_db)

    def test_create_cycle(self, test_db: Session, test_user: User):
        """Test creating a new cycle."""
        cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        assert cycle is not None
        assert cycle.user_id == test_user.id
        assert cycle.start_date == date(2025, 9, 1)
        assert cycle.cycle_length == 28
        assert cycle.period_length == 5
        assert cycle.is_current is True
        assert cycle.created_at is not None

    def test_get_cycle(self, test_db: Session, test_user: User):
        """Test getting a cycle by ID."""
        # Create cycle
        created_cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        # Get cycle by ID
        cycle = get_cycle_by_id(session=test_db, cycle_id=created_cycle.id)

        assert cycle is not None
        assert cycle.id == created_cycle.id
        assert cycle.start_date == date(2025, 9, 1)

    def test_get_current_cycle(self, test_db: Session, test_user: User):
        """Test getting the current active cycle."""
        # Create multiple cycles
        old_cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 8, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        # Mark old cycle as not current
        update_cycle_status(test_db, old_cycle.id, is_current=False)

        # Create current cycle
        current_cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        # Get current cycle
        fetched_cycle = get_current_cycle(user_id=test_user.id, session=test_db)

        assert fetched_cycle is not None
        assert fetched_cycle.id == current_cycle.id
        assert fetched_cycle.is_current is True
        assert fetched_cycle.start_date == date(2025, 9, 1)

    def test_get_user_cycles(self, test_db: Session, test_user: User):
        """Test getting all cycles for a user."""
        # Create multiple cycles
        dates = [
            date(2025, 7, 1),
            date(2025, 8, 1),
            date(2025, 9, 1)
        ]

        for start_date in dates:
            create_cycle(
                user_id=test_user.id,
                start_date=start_date,
                cycle_length=28,
                period_length=5,
                session=test_db
            )

        # Get all cycles
        cycles = get_user_cycles(user_id=test_user.id, session=test_db)

        assert len(cycles) == 3
        cycle_dates = [cycle.start_date for cycle in cycles]
        for date_val in dates:
            assert date_val in cycle_dates

    def test_update_cycle(self, test_db: Session, test_user: User):
        """Test updating cycle data."""
        # Create cycle
        cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        # Update cycle
        updated_cycle = update_cycle(
            cycle_id=cycle.id,
            updates={
                "cycle_length": 30,
                "period_length": 7
            },
            session=test_db
        )

        assert updated_cycle is not None
        assert updated_cycle.cycle_length == 30
        assert updated_cycle.period_length == 7
        assert updated_cycle.start_date == date(2025, 9, 1)  # Should not change

    def test_update_cycle_dates(self, test_db: Session, test_user: User):
        """Test updating cycle start date."""
        # Create cycle
        cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        # Update start date
        updated_cycle = update_cycle(
            cycle_id=cycle.id,
            updates={
                "start_date": date(2025, 9, 15)
            },
            session=test_db
        )

        assert updated_cycle is not None
        assert updated_cycle.start_date == date(2025, 9, 15)
        assert updated_cycle.cycle_length == 28  # Should not change

    def test_update_cycle_status(self, test_db: Session, test_user: User):
        """Test updating cycle active status."""
        # Create cycle
        cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        assert cycle.is_current is True

        # Mark as not current
        updated_cycle = update_cycle_status(test_db, cycle.id, is_current=False)

        assert updated_cycle is not None
        assert updated_cycle.is_current is False

    def test_delete_cycle(self, test_db: Session, test_user: User):
        """Test deleting a cycle."""
        # Create cycle
        cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )
        cycle_id = cycle.id

        # Delete cycle
        success = delete_cycle(cycle_id=cycle_id, session=test_db)
        assert success is True

        # Verify cycle is deleted
        deleted_cycle = get_cycle_by_id(session=test_db, cycle_id=cycle_id)
        assert deleted_cycle is None

    def test_auto_deactivate_old_cycles(self, test_db: Session, test_user: User):
        """Test that creating a new cycle deactivates old ones."""
        # Create first cycle
        first_cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 8, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        assert first_cycle.is_current is True

        # Create second cycle with is_current=True (this should deactivate the first)
        second_cycle = create_cycle(
            user_id=test_user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            is_current=True,
            session=test_db
        )

        # Get the first cycle again from database to check its status
        first_cycle_updated = get_cycle_by_id(session=test_db, cycle_id=first_cycle.id)

        # Check that first cycle is now inactive
        assert first_cycle_updated.is_current is False
        assert second_cycle.is_current is True


class TestNotificationSettingsCRUD:
    """Test NotificationSettings model CRUD operations."""

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user for notification settings tests."""
        return create_user(telegram_id=12345, username="test_user", session=test_db)

    def test_create_notification_setting(self, test_db: Session, test_user: User):
        """Test creating notification settings."""
        # Create a single notification setting
        setting = create_notification_settings(
            user_id=test_user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            is_enabled=True,
            time_offset=0,
            session=test_db
        )

        assert setting is not None
        assert setting.user_id == test_user.id
        assert setting.notification_type == NotificationType.PERIOD_REMINDER.value
        assert setting.is_enabled is True
        assert setting.time_offset == 0

    def test_get_notification_settings(self, test_db: Session, test_user: User):
        """Test getting all notification settings for a user."""
        # Create multiple notification settings
        for notif_type in [NotificationType.PERIOD_REMINDER, NotificationType.OVULATION_DAY]:
            create_notification_settings(
                user_id=test_user.id,
                notification_type=notif_type.value,
                is_enabled=True,
                session=test_db
            )

        # Get all settings
        settings = get_user_notification_settings(user_id=test_user.id, session=test_db)

        assert len(settings) == 2
        setting_types = [s.notification_type for s in settings]
        assert NotificationType.PERIOD_REMINDER.value in setting_types
        assert NotificationType.OVULATION_DAY.value in setting_types

    def test_update_notification_setting(self, test_db: Session, test_user: User):
        """Test updating notification settings."""
        # Create setting first
        create_notification_settings(
            user_id=test_user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            is_enabled=True,
            session=test_db
        )

        # Update single setting
        updated_setting = update_notification_setting(
            user_id=test_user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            is_enabled=False,
            session=test_db
        )

        assert updated_setting is not None
        assert updated_setting.is_enabled is False
        assert updated_setting.notification_type == NotificationType.PERIOD_REMINDER.value

    def test_update_multiple_notification_settings(self, test_db: Session, test_user: User):
        """Test updating multiple notification settings at once."""
        # Create settings first
        settings = []
        for notif_type in [NotificationType.PERIOD_REMINDER, NotificationType.OVULATION_DAY, NotificationType.FERTILE_WINDOW_START]:
            setting = create_notification_settings(
                user_id=test_user.id,
                notification_type=notif_type.value,
                is_enabled=True,
                session=test_db
            )
            settings.append(setting)

        # Update each setting individually
        for notif_type in [NotificationType.PERIOD_REMINDER, NotificationType.OVULATION_DAY]:
            update_notification_setting(
                user_id=test_user.id,
                notification_type=notif_type.value,
                is_enabled=False,
                session=test_db
            )

        # Verify updates
        all_settings = get_user_notification_settings(user_id=test_user.id, session=test_db)
        for setting in all_settings:
            if setting.notification_type in [NotificationType.PERIOD_REMINDER.value, NotificationType.OVULATION_DAY.value]:
                assert setting.is_enabled is False
            else:
                assert setting.is_enabled is True

    def test_unique_notification_type_per_user(self, test_db: Session, test_user: User):
        """Test that each user can have only one setting per notification type."""
        # Create initial setting
        setting1 = create_notification_settings(
            user_id=test_user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            is_enabled=True,
            session=test_db
        )

        # Try to create duplicate - should return existing
        setting2 = create_notification_settings(
            user_id=test_user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            is_enabled=False,
            session=test_db
        )

        # Should return existing setting
        assert setting2.id == setting1.id
        assert setting2.is_enabled is True  # Original value is preserved


class TestNotificationLogCRUD:
    """Test NotificationLog model CRUD operations."""

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user for notification log tests."""
        return create_user(telegram_id=12345, username="test_user", session=test_db)

    def test_create_notification_log(self, test_db: Session, test_user: User):
        """Test creating a notification log entry."""
        # Create notification log directly due to missing scheduled_at in crud function
        from datetime import datetime
        log_entry = NotificationLog(
            user_id=test_user.id,
            notification_type=NotificationType.OVULATION_DAY.value,
            scheduled_at=datetime.utcnow(),
            sent_at=datetime.utcnow(),
            status="sent",
            error_message=None
        )
        test_db.add(log_entry)
        test_db.commit()
        test_db.refresh(log_entry)

        assert log_entry is not None
        assert log_entry.user_id == test_user.id
        assert log_entry.notification_type == NotificationType.OVULATION_DAY.value
        assert log_entry.status == "sent"
        assert log_entry.error_message is None
        assert log_entry.sent_at is not None

    def test_get_notification_logs(self, test_db: Session, test_user: User):
        """Test getting notification logs for a user."""
        # Create multiple log entries directly
        from datetime import datetime
        statuses = ["sent", "failed", "sent"]
        for i, status in enumerate(statuses):
            log = NotificationLog(
                user_id=test_user.id,
                notification_type=NotificationType.PERIOD_REMINDER.value,
                scheduled_at=datetime.utcnow(),
                sent_at=datetime.utcnow() if status == "sent" else None,
                status=status,
                error_message=f"Error {i+1}" if status == "failed" else None
            )
            test_db.add(log)
        test_db.commit()

        # Get all logs
        logs = get_user_notification_logs(user_id=test_user.id, session=test_db)

        assert len(logs) == 3
        log_statuses = [log.status for log in logs]
        assert "sent" in log_statuses
        assert "failed" in log_statuses

    def test_get_notification_logs_with_limit(self, test_db: Session, test_user: User):
        """Test getting limited number of notification logs."""
        # Create 10 log entries directly
        from datetime import datetime
        for i in range(10):
            log = NotificationLog(
                user_id=test_user.id,
                notification_type=NotificationType.PERIOD_REMINDER.value,
                scheduled_at=datetime.utcnow(),
                sent_at=datetime.utcnow(),
                status="sent"
            )
            test_db.add(log)
        test_db.commit()

        # Get only 5 logs
        logs = get_user_notification_logs(user_id=test_user.id, limit=5, session=test_db)

        assert len(logs) == 5

    def test_get_notification_logs_by_type(self, test_db: Session, test_user: User):
        """Test filtering notification logs by type."""
        # Create logs with different types directly
        from datetime import datetime
        log_types = [
            NotificationType.PERIOD_REMINDER.value,
            NotificationType.OVULATION_DAY.value,
            NotificationType.PERIOD_REMINDER.value
        ]

        for log_type in log_types:
            log = NotificationLog(
                user_id=test_user.id,
                notification_type=log_type,
                scheduled_at=datetime.utcnow(),
                sent_at=datetime.utcnow(),
                status="sent"
            )
            test_db.add(log)
        test_db.commit()

        # Get logs for specific type
        logs = get_user_notification_logs(
            user_id=test_user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            session=test_db
        )

        assert len(logs) == 2
        for log in logs:
            assert log.notification_type == NotificationType.PERIOD_REMINDER.value


class TestCascadeDeleteOperations:
    """Test cascade delete operations between related models."""

    def test_cascade_delete_user(self, test_db: Session):
        """Test that deleting a user cascades to related records."""
        # Create user
        user = create_user(telegram_id=12345, username="test_user", session=test_db)

        # Create related records
        cycle = create_cycle(
            user_id=user.id,
            start_date=date(2025, 9, 1),
            cycle_length=28,
            period_length=5,
            session=test_db
        )

        notification_setting = create_notification_settings(
            user_id=user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            session=test_db
        )

        # Create notification log directly due to missing scheduled_at in crud function
        from datetime import datetime
        notification_log = NotificationLog(
            user_id=user.id,
            notification_type=NotificationType.PERIOD_REMINDER.value,
            scheduled_at=datetime.utcnow(),
            sent_at=datetime.utcnow(),
            status="sent"
        )
        test_db.add(notification_log)
        test_db.commit()
        test_db.refresh(notification_log)

        # Store IDs for verification
        cycle_id = cycle.id
        setting_id = notification_setting.id
        log_id = notification_log.id

        # Delete user
        success = delete_user(telegram_id=12345, session=test_db)
        assert success is True

        # Verify all related records are deleted
        assert get_cycle_by_id(session=test_db, cycle_id=cycle_id) is None

        # Check notification setting is deleted
        assert test_db.query(NotificationSettings).filter_by(id=setting_id).first() is None

        assert test_db.query(NotificationLog).filter_by(id=log_id).first() is None


class TestTransactionIsolation:
    """Test transaction isolation and rollback behavior."""

    def test_rollback_on_error(self, test_db: Session):
        """Test that errors properly rollback transactions."""
        # Create user
        user = create_user(telegram_id=12345, username="test_user", session=test_db)

        try:
            # Try to create invalid cycle (invalid date)
            cycle = Cycle(
                user_id=user.id,
                start_date=None,  # Invalid: required field
                cycle_length=28,
                period_length=5
            )
            test_db.add(cycle)
            test_db.commit()
        except Exception:
            test_db.rollback()

        # Verify user still exists and no cycles were created
        assert get_user(user_id=user.id, session=test_db) is not None
        assert len(get_user_cycles(user_id=user.id, session=test_db)) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_username(self, test_db: Session):
        """Test creating user with empty username."""
        user = create_user(telegram_id=12345, username="", session=test_db)
        assert user is not None
        assert user.username == ""

    def test_none_username(self, test_db: Session):
        """Test creating user with None username."""
        user = create_user(telegram_id=12345, username=None, session=test_db)
        assert user is not None
        assert user.username is None

    def test_boundary_cycle_lengths(self, test_db: Session):
        """Test cycles with boundary values."""
        user = create_user(telegram_id=12345, username="test_user", session=test_db)

        # Minimum values
        min_cycle = create_cycle(
            user_id=user.id,
            start_date=date(2025, 9, 1),
            cycle_length=21,  # Minimum allowed
            period_length=1,  # Minimum allowed
            session=test_db
        )
        assert min_cycle is not None
        assert min_cycle.cycle_length == 21
        assert min_cycle.period_length == 1

        # Maximum values
        update_cycle_status(test_db, min_cycle.id, is_current=False)
        max_cycle = create_cycle(
            user_id=user.id,
            start_date=date(2025, 10, 1),
            cycle_length=40,  # Maximum allowed
            period_length=10,  # Maximum allowed
            session=test_db
        )
        assert max_cycle is not None
        assert max_cycle.cycle_length == 40
        assert max_cycle.period_length == 10

    def test_concurrent_cycles_same_user(self, test_db: Session):
        """Test that only one cycle can be current for a user."""
        user = create_user(telegram_id=12345, username="test_user", session=test_db)

        # Create multiple cycles
        cycles = []
        for i in range(5):
            cycle = create_cycle(
                user_id=user.id,
                start_date=date(2025, 9 - i, 1),
                cycle_length=28,
                period_length=5,
                session=test_db
            )
            cycles.append(cycle)

        # Get all cycles from database to check their current status
        all_cycles = get_user_cycles(user_id=user.id, session=test_db)

        # Count current cycles
        current_cycles = [c for c in all_cycles if c.is_current]
        assert len(current_cycles) == 1

        # The last created cycle should be current
        assert cycles[-1].is_current is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])