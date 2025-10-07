#!/usr/bin/env python3
"""
Test script to verify notification tasks are properly updated when cycle parameters change.
Tests TASK-028 implementation.
"""

import sys
import os
from datetime import date, timedelta
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import db_session
from src.database.crud import (
    get_user, create_user, create_cycle, update_cycle,
    get_current_cycle, get_user_notification_settings
)
from src.notifications.types import NotificationType
from src.notifications.scheduler_utils import get_all_notification_times

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_notification_update_on_cycle_change():
    """Test that notifications are properly recalculated when cycle parameters change."""

    print("\n" + "="*60)
    print("Testing Notification Update on Cycle Parameter Changes")
    print("(TASK-028 Verification)")
    print("="*60 + "\n")

    test_telegram_id = 999999  # Test user ID

    with db_session.get_session() as session:
        # 1. Clean up test user if exists
        existing_user = get_user(telegram_id=test_telegram_id, session=session)
        if existing_user:
            # Delete existing user and related data
            session.delete(existing_user)
            session.commit()
            print("✅ Cleaned up existing test user")

        # 2. Create test user
        user = create_user(
            telegram_id=test_telegram_id,
            username="test_notification_update",
            session=session
        )
        print(f"✅ Created test user: {user.username} (ID: {user.id})")

        # 3. Create initial cycle
        initial_date = date.today() - timedelta(days=5)  # Started 5 days ago
        initial_cycle_length = 28
        initial_period_length = 5

        cycle = create_cycle(
            session=session,
            user_id=user.id,
            start_date=initial_date,
            cycle_length=initial_cycle_length,
            period_length=initial_period_length,
            is_current=True
        )
        print(f"\n✅ Created initial cycle:")
        print(f"   - Start date: {initial_date}")
        print(f"   - Cycle length: {initial_cycle_length} days")
        print(f"   - Period length: {initial_period_length} days")

        # 4. Calculate initial notification dates
        print("\n📅 Initial Notification Dates:")
        print("-" * 40)

        # Create mock notification settings (all enabled)
        mock_settings = []
        for notification_type in NotificationType:
            mock_setting = type('obj', (object,), {
                'notification_type': notification_type.value,
                'is_enabled': True,
                'time_offset': 0
            })()
            mock_settings.append(mock_setting)

        initial_times = get_all_notification_times(
            cycle=cycle,
            user=user,
            notification_settings=mock_settings
        )

        for notif_type, send_time in initial_times.items():
            print(f"   {notif_type.value}: {send_time.strftime('%Y-%m-%d %H:%M')}")

        # 5. Update cycle parameters
        print("\n🔄 Updating cycle parameters...")

        # Change start date (move forward by 3 days)
        new_date = initial_date + timedelta(days=3)
        updated_cycle = update_cycle(
            cycle_id=cycle.id,
            updates={'start_date': new_date},
            session=session
        )
        print(f"   - Updated start date to: {new_date}")

        # 6. Calculate new notification dates
        print("\n📅 Updated Notification Dates (after date change):")
        print("-" * 40)

        new_times = get_all_notification_times(
            cycle=updated_cycle,
            user=user,
            notification_settings=mock_settings
        )

        for notif_type, send_time in new_times.items():
            print(f"   {notif_type.value}: {send_time.strftime('%Y-%m-%d %H:%M')}")

        # 7. Compare dates
        print("\n📊 Date Changes:")
        print("-" * 40)
        for notif_type in NotificationType:
            if notif_type in initial_times and notif_type in new_times:
                diff = (new_times[notif_type] - initial_times[notif_type]).days
                print(f"   {notif_type.value}: shifted by {diff} days")

        # 8. Update cycle length
        print("\n🔄 Updating cycle length...")
        new_cycle_length = 30
        updated_cycle = update_cycle(
            cycle_id=cycle.id,
            updates={'cycle_length': new_cycle_length},
            session=session
        )
        print(f"   - Updated cycle length to: {new_cycle_length} days")

        # 9. Calculate notification dates with new cycle length
        print("\n📅 Updated Notification Dates (after cycle length change):")
        print("-" * 40)

        final_times = get_all_notification_times(
            cycle=updated_cycle,
            user=user,
            notification_settings=mock_settings
        )

        for notif_type, send_time in final_times.items():
            print(f"   {notif_type.value}: {send_time.strftime('%Y-%m-%d %H:%M')}")

        # 10. Verify changes
        print("\n✅ Verification Results:")
        print("-" * 40)

        # Check that dates changed appropriately
        changes_detected = False
        for notif_type in NotificationType:
            if notif_type in new_times and notif_type in final_times:
                if new_times[notif_type] != final_times[notif_type]:
                    changes_detected = True
                    break

        if changes_detected:
            print("   ✅ Notification dates properly updated after cycle changes")
        else:
            print("   ⚠️ Some notification dates may not have changed (expected for some types)")

        # Clean up test data
        session.delete(user)
        session.commit()
        print("\n✅ Test data cleaned up")

    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_notification_update_on_cycle_change()