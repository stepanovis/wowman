"""
Cycle model for storing menstrual cycle information.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, Date, Boolean, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from .base import Base


class Cycle(Base):
    """
    Model for storing menstrual cycle information.
    """
    __tablename__ = 'cycles'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Cycle parameters
    start_date = Column(Date, nullable=False, index=True)
    cycle_length = Column(Integer, nullable=False)
    period_length = Column(Integer, nullable=False)

    # Status
    is_current = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional notes
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship('User', back_populates='cycles')

    # Constraints
    __table_args__ = (
        CheckConstraint('cycle_length >= 21 AND cycle_length <= 40', name='check_cycle_length'),
        CheckConstraint('period_length >= 1 AND period_length <= 10', name='check_period_length'),
    )

    def __repr__(self):
        """String representation of the Cycle model."""
        return (
            f"<Cycle(id={self.id}, "
            f"user_id={self.user_id}, "
            f"start_date={self.start_date}, "
            f"cycle_length={self.cycle_length}, "
            f"period_length={self.period_length}, "
            f"is_current={self.is_current})>"
        )

    def get_next_period_date(self):
        """Calculate the next period start date."""
        if self.start_date and self.cycle_length:
            return self.start_date + timedelta(days=self.cycle_length)
        return None

    def get_ovulation_date(self):
        """Calculate the approximate ovulation date."""
        if self.start_date and self.cycle_length:
            # Ovulation typically occurs 14 days before the next period
            return self.start_date + timedelta(days=self.cycle_length - 14)
        return None

    def get_fertile_window_start(self):
        """Calculate the start of the fertile window (5 days before ovulation)."""
        ovulation = self.get_ovulation_date()
        if ovulation:
            return ovulation - timedelta(days=5)
        return None

    def get_fertile_window_end(self):
        """Calculate the end of the fertile window (1 day after ovulation)."""
        ovulation = self.get_ovulation_date()
        if ovulation:
            return ovulation + timedelta(days=1)
        return None

    def get_period_end_date(self):
        """Calculate when the period ends."""
        if self.start_date and self.period_length:
            return self.start_date + timedelta(days=self.period_length - 1)
        return None

    def is_period_day(self, date):
        """Check if a given date is during the period."""
        if not self.start_date or not self.period_length:
            return False
        period_end = self.get_period_end_date()
        return self.start_date <= date <= period_end

    def is_fertile_day(self, date):
        """Check if a given date is during the fertile window."""
        fertile_start = self.get_fertile_window_start()
        fertile_end = self.get_fertile_window_end()
        if fertile_start and fertile_end:
            return fertile_start <= date <= fertile_end
        return False

    def get_current_day_of_cycle(self, date=None):
        """Get the current day number in the cycle."""
        if not date:
            date = datetime.now().date()
        if self.start_date:
            delta = date - self.start_date
            return delta.days + 1
        return None

    def set_as_current(self):
        """Set this cycle as the current active cycle."""
        # First, deactivate all other cycles for this user
        Cycle.query.filter_by(user_id=self.user_id, is_current=True).update({'is_current': False})
        # Then set this one as current
        self.is_current = True