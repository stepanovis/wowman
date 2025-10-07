"""
User model for storing Telegram user information.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """
    Model for storing user information.
    """
    __tablename__ = 'users'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Telegram user information
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)

    # User preferences
    timezone = Column(String(50), default='Europe/Moscow', nullable=False)
    preferred_language = Column(String(10), default='ru', nullable=False)

    # User status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_active_at = Column(DateTime, nullable=True)
    commands_count = Column(Integer, default=0, nullable=False)

    # Relationships
    cycles = relationship(
        'Cycle',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    notification_settings = relationship(
        'NotificationSettings',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    notification_logs = relationship(
        'NotificationLog',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def __repr__(self):
        """String representation of the User model."""
        return (
            f"<User(id={self.id}, "
            f"telegram_id={self.telegram_id}, "
            f"username='{self.username}', "
            f"is_active={self.is_active})>"
        )

    def get_current_cycle(self):
        """Get the current active cycle for this user."""
        return self.cycles.filter_by(is_current=True).first()

    def increment_command_count(self):
        """Increment the command count and update last active time."""
        self.commands_count += 1
        self.last_active_at = datetime.utcnow()

    def deactivate(self):
        """Deactivate the user (e.g., when bot is blocked)."""
        self.is_active = False

    def activate(self):
        """Activate the user."""
        self.is_active = True