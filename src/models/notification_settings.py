"""
NotificationSettings model for storing user notification preferences.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


class NotificationSettings(Base):
    """
    Model for storing user notification preferences.
    """
    __tablename__ = 'notification_settings'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    # Notification type (enum-like string)
    notification_type = Column(String(50), nullable=False)

    # Settings
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)
    time_offset = Column(Integer, default=0, nullable=False)  # Offset in minutes from default time
    custom_time = Column(Time, nullable=True)  # Custom time for notification

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='notification_settings')

    # Unique constraint - one setting per notification type per user
    __table_args__ = (
        UniqueConstraint('user_id', 'notification_type', name='unique_user_notification_type'),
    )

    # Notification types as class constants
    PERIOD_REMINDER = 'PERIOD_REMINDER'
    PERIOD_START = 'PERIOD_START'
    FERTILE_WINDOW_START = 'FERTILE_WINDOW_START'
    OVULATION_DAY = 'OVULATION_DAY'
    SAFE_PERIOD = 'SAFE_PERIOD'

    # All notification types
    NOTIFICATION_TYPES = [
        PERIOD_REMINDER,
        PERIOD_START,
        FERTILE_WINDOW_START,
        OVULATION_DAY,
        SAFE_PERIOD
    ]

    def __repr__(self):
        """String representation of the NotificationSettings model."""
        return (
            f"<NotificationSettings(id={self.id}, "
            f"user_id={self.user_id}, "
            f"type='{self.notification_type}', "
            f"is_enabled={self.is_enabled})>"
        )

    def enable(self):
        """Enable this notification."""
        self.is_enabled = True
        self.updated_at = datetime.utcnow()

    def disable(self):
        """Disable this notification."""
        self.is_enabled = False
        self.updated_at = datetime.utcnow()

    def set_custom_time(self, time):
        """Set a custom time for this notification."""
        self.custom_time = time
        self.updated_at = datetime.utcnow()

    def set_time_offset(self, offset_minutes):
        """Set time offset in minutes from the default time."""
        self.time_offset = offset_minutes
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_notification_description(cls, notification_type):
        """Get human-readable description for notification type."""
        descriptions = {
            cls.PERIOD_REMINDER: "Напоминание о приближении месячных (за 2 дня)",
            cls.PERIOD_START: "Уведомление о начале месячных",
            cls.FERTILE_WINDOW_START: "Начало фертильного окна",
            cls.OVULATION_DAY: "День овуляции",
            cls.SAFE_PERIOD: "Начало безопасного периода"
        }
        return descriptions.get(notification_type, "Неизвестный тип уведомления")

    @classmethod
    def get_default_offset_days(cls, notification_type):
        """Get default days offset for each notification type."""
        offsets = {
            cls.PERIOD_REMINDER: -2,  # 2 days before period
            cls.PERIOD_START: 0,      # Day of period start
            cls.FERTILE_WINDOW_START: -5,  # 5 days before ovulation
            cls.OVULATION_DAY: 0,      # Day of ovulation
            cls.SAFE_PERIOD: 2         # 2 days after ovulation
        }
        return offsets.get(notification_type, 0)