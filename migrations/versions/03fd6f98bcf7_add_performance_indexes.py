"""add_performance_indexes

Revision ID: 03fd6f98bcf7
Revises: 818750be4886
Create Date: 2025-10-01 09:41:24.210137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03fd6f98bcf7'
down_revision: Union[str, Sequence[str], None] = '818750be4886'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add performance indexes for common queries."""

    # Composite indexes for frequently joined/filtered columns

    # 1. Composite index for cycles table - user_id + is_current (very common query pattern)
    op.create_index(
        'ix_cycles_user_id_is_current',
        'cycles',
        ['user_id', 'is_current'],
        unique=False
    )

    # 2. Composite index for cycles table - user_id + start_date for date range queries
    op.create_index(
        'ix_cycles_user_id_start_date',
        'cycles',
        ['user_id', 'start_date'],
        unique=False
    )

    # 3. Composite index for notification_settings - user_id + notification_type (unique constraint already exists, but add index)
    op.create_index(
        'ix_notification_settings_user_id_notification_type',
        'notification_settings',
        ['user_id', 'notification_type'],
        unique=False
    )

    # 4. Composite index for notification_settings - user_id + is_enabled
    op.create_index(
        'ix_notification_settings_user_id_is_enabled',
        'notification_settings',
        ['user_id', 'is_enabled'],
        unique=False
    )

    # 5. Composite index for notification_log - user_id + notification_type + sent_at for filtered queries
    op.create_index(
        'ix_notification_log_user_id_type_sent',
        'notification_log',
        ['user_id', 'notification_type', 'sent_at'],
        unique=False
    )

    # 6. Index for notification_log scheduled_at (for finding pending notifications)
    op.create_index(
        'ix_notification_log_scheduled_at',
        'notification_log',
        ['scheduled_at'],
        unique=False
    )

    # 7. Composite index for notification_log - status + scheduled_at (for pending notifications)
    op.create_index(
        'ix_notification_log_status_scheduled',
        'notification_log',
        ['status', 'scheduled_at'],
        unique=False
    )

    # 8. Index for users.last_active_at (for analytics and cleanup)
    op.create_index(
        'ix_users_last_active_at',
        'users',
        ['last_active_at'],
        unique=False
    )

    # 9. Composite index for users - is_active + last_active_at (for finding active users)
    op.create_index(
        'ix_users_is_active_last_active',
        'users',
        ['is_active', 'last_active_at'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema - Remove performance indexes."""

    # Remove composite indexes in reverse order
    op.drop_index('ix_users_is_active_last_active', table_name='users')
    op.drop_index('ix_users_last_active_at', table_name='users')
    op.drop_index('ix_notification_log_status_scheduled', table_name='notification_log')
    op.drop_index('ix_notification_log_scheduled_at', table_name='notification_log')
    op.drop_index('ix_notification_log_user_id_type_sent', table_name='notification_log')
    op.drop_index('ix_notification_settings_user_id_is_enabled', table_name='notification_settings')
    op.drop_index('ix_notification_settings_user_id_notification_type', table_name='notification_settings')
    op.drop_index('ix_cycles_user_id_start_date', table_name='cycles')
    op.drop_index('ix_cycles_user_id_is_current', table_name='cycles')
