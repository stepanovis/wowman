"""
NotificationLog model for tracking sent notifications.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class NotificationLog(Base):
    """
    Model for logging notification sending attempts and results.
    """
    __tablename__ = 'notification_log'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Notification details
    notification_type = Column(String(50), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True, index=True)

    # Status
    status = Column(String(20), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='notification_logs')

    # Status constants
    STATUS_SCHEDULED = 'SCHEDULED'
    STATUS_SENT = 'SENT'
    STATUS_FAILED = 'FAILED'
    STATUS_RETRY = 'RETRY'
    STATUS_CANCELLED = 'CANCELLED'

    # All statuses
    STATUSES = [
        STATUS_SCHEDULED,
        STATUS_SENT,
        STATUS_FAILED,
        STATUS_RETRY,
        STATUS_CANCELLED
    ]

    def __repr__(self):
        """String representation of the NotificationLog model."""
        return (
            f"<NotificationLog(id={self.id}, "
            f"user_id={self.user_id}, "
            f"type='{self.notification_type}', "
            f"status='{self.status}', "
            f"sent_at={self.sent_at})>"
        )

    def mark_as_sent(self):
        """Mark notification as successfully sent."""
        self.status = self.STATUS_SENT
        self.sent_at = datetime.utcnow()
        self.error_message = None

    def mark_as_failed(self, error_message=None):
        """Mark notification as failed."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message

    def mark_for_retry(self):
        """Mark notification for retry."""
        self.status = self.STATUS_RETRY
        self.retry_count += 1

    def mark_as_cancelled(self):
        """Mark notification as cancelled."""
        self.status = self.STATUS_CANCELLED

    def is_successful(self):
        """Check if notification was sent successfully."""
        return self.status == self.STATUS_SENT

    def is_failed(self):
        """Check if notification failed."""
        return self.status == self.STATUS_FAILED

    def can_retry(self, max_retries=3):
        """Check if notification can be retried."""
        return self.status != self.STATUS_SENT and self.retry_count < max_retries

    @classmethod
    def get_recent_logs(cls, user_id, days=30):
        """Get recent notification logs for a user."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.user_id == user_id,
            cls.created_at >= cutoff_date
        ).order_by(cls.created_at.desc())

    @classmethod
    def get_success_rate(cls, user_id, notification_type=None, days=30):
        """Calculate success rate for notifications."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = cls.query.filter(
            cls.user_id == user_id,
            cls.created_at >= cutoff_date
        )

        if notification_type:
            query = query.filter(cls.notification_type == notification_type)

        total = query.count()
        if total == 0:
            return 0.0

        successful = query.filter(cls.status == cls.STATUS_SENT).count()
        return (successful / total) * 100