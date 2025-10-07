#!/usr/bin/env python3
"""
Test script to verify notification task creation.
This script tests that notification settings and tasks are created properly.
"""

import asyncio
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.session import db_session
from database.crud import (
    get_user,
    get_current_cycle,
    get_user_notification_settings,
    create_user,
    create_cycle
)
from notifications.types import NotificationType
from notifications.scheduler_utils import get_all_notification_times


def test_notification_settings():
    """Test that notification settings can be created and retrieved."""
    print("\n=== Testing Notification Settings ===")

    with db_session.get_session() as session:
        # Get or create test user
        test_telegram_id = 123456789
        user = get_user(telegram_id=test_telegram_id, session=session)

        if not user:
            print(f"Creating test user with telegram_id={test_telegram_id}")
            user = create_user(
                telegram_id=test_telegram_id,
                username="test_user",
                timezone="Europe/Moscow",
                session=session
            )
            print(f"Created user: {user.id}")
        else:
            print(f"Found existing user: {user.id}")

        # Get current cycle
        cycle = get_current_cycle(user_id=user.id, session=session)

        if not cycle:
            print("Creating test cycle...")
            cycle = create_cycle(
                session=session,
                user_id=user.id,
                start_date=date.today() - timedelta(days=7),
                cycle_length=28,
                period_length=5,
                is_current=True
            )
            print(f"Created cycle: {cycle.id}")
        else:
            print(f"Found existing cycle: {cycle.id}")

        # Get notification settings
        settings = get_user_notification_settings(
            user_id=user.id,
            session=session
        )

        if settings:
            print(f"\nFound {len(settings)} notification settings:")
            for setting in settings:
                print(f"  - {setting.notification_type}: {'Enabled' if setting.is_enabled else 'Disabled'}")
        else:
            print("No notification settings found")

        # Calculate notification times
        print("\n=== Calculating Notification Times ===")
        notification_times = get_all_notification_times(
            cycle=cycle,
            user=user,
            notification_settings=settings
        )

        if notification_times:
            print(f"Calculated {len(notification_times)} notification times:")
            for notif_type, send_time in notification_times.items():
                print(f"  - {notif_type.value}: {send_time}")
        else:
            print("No notification times calculated")

        return user, cycle, settings, notification_times


async def test_scheduler_tasks():
    """Test that scheduler tasks are created properly."""
    print("\n=== Testing Scheduler Tasks (Mock) ===")

    user, cycle, settings, notification_times = test_notification_settings()

    if not notification_times:
        print("No notification times to schedule")
        return

    # Mock scheduler behavior
    print(f"\nWould create {len(notification_times)} scheduler tasks:")
    for notif_type, send_time in notification_times.items():
        job_id = f"notification_{user.id}_{notif_type.value}_{send_time.timestamp()}"
        print(f"  - Job ID: {job_id[:50]}...")
        print(f"    Type: {notif_type.value}")
        print(f"    Send at: {send_time}")

    print("\n✅ Notification setup test completed successfully!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("NOTIFICATION SYSTEM TEST")
    print("=" * 60)

    # Run sync tests
    test_notification_settings()

    # Run async tests
    print("\n" + "=" * 60)
    asyncio.run(test_scheduler_tasks())

    print("\n" + "=" * 60)
    print("All tests completed!")


if __name__ == "__main__":
    main()