#!/usr/bin/env python3
"""
Simple test to verify notification task creation is working.
This test checks the database directly without complex imports.
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.session import db_session
from database.crud import (
    get_user,
    get_current_cycle,
    get_user_notification_settings,
)


def test_notification_database():
    """Test that notification settings are being saved to database."""
    print("\n=== Testing Notification Database Records ===")

    with db_session.get_session() as session:
        # Use a known test user ID (you can replace with an actual user ID)
        test_telegram_id = 123456789

        # Get user
        user = get_user(telegram_id=test_telegram_id, session=session)

        if not user:
            print(f"No user found with telegram_id={test_telegram_id}")
            print("Please run the bot and use /start and /setup commands first")
            return

        print(f"Found user: {user.username} (ID: {user.id})")

        # Get current cycle
        cycle = get_current_cycle(user_id=user.id, session=session)

        if not cycle:
            print("No current cycle found for user")
            print("Please run /setup command first")
            return

        print(f"\nCurrent cycle:")
        print(f"  Start date: {cycle.start_date}")
        print(f"  Cycle length: {cycle.cycle_length} days")
        print(f"  Period length: {cycle.period_length} days")

        # Get notification settings
        settings = get_user_notification_settings(
            user_id=user.id,
            session=session
        )

        if not settings:
            print("\n❌ No notification settings found")
            print("Notification task creation may not be working")
        else:
            print(f"\n✅ Found {len(settings)} notification settings:")
            for setting in settings:
                status = "Enabled" if setting.is_enabled else "Disabled"
                print(f"  - {setting.notification_type}: {status}")

        # Check if APScheduler jobs table exists and has entries
        try:
            result = session.execute("SELECT COUNT(*) FROM apscheduler_jobs")
            job_count = result.scalar()
            print(f"\n📅 APScheduler has {job_count} job(s) in database")

            if job_count > 0:
                # Get some job details
                result = session.execute(
                    "SELECT id, next_run_time FROM apscheduler_jobs LIMIT 5"
                )
                print("Sample jobs:")
                for row in result:
                    job_id = row[0]
                    # Extract user_id from job_id if it matches our pattern
                    if f"notification_{user.id}_" in job_id:
                        print(f"  ✅ Found job for user {user.id}: {job_id[:60]}...")
        except Exception as e:
            print(f"\n⚠️ Could not check APScheduler jobs table: {e}")
            print("This is normal if the scheduler hasn't been initialized yet")

    print("\n" + "=" * 60)


def main():
    """Run the test."""
    print("=" * 60)
    print("NOTIFICATION SYSTEM DATABASE TEST")
    print("=" * 60)

    test_notification_database()

    print("\nTest completed!")
    print("\nNext steps to fully test:")
    print("1. Run the bot: python src/main.py")
    print("2. Use /start command in Telegram")
    print("3. Use /setup command to configure cycle")
    print("4. Run this test again to see if notification settings were created")
    print("5. Check bot logs for 'Created X notification tasks' messages")


if __name__ == "__main__":
    main()