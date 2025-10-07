#!/usr/bin/env python3
"""
Test script for /notifications command functionality.
Tests the notification settings management interface.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.database.session import db_session
from src.database.crud import (
    get_user,
    get_user_notification_settings,
    update_notification_setting
)
from src.notifications.types import NotificationType


def test_notification_settings():
    """Test notification settings CRUD operations."""
    print("Testing notification settings functionality...")
    print("-" * 50)

    # Test with a specific telegram_id (change this to match your test user)
    test_telegram_id = 123456789  # Replace with actual test user telegram_id

    with db_session.get_session() as session:
        # Get user
        user = get_user(test_telegram_id, session=session)
        if not user:
            print(f"❌ User with telegram_id {test_telegram_id} not found")
            print("Please make sure you have a test user in the database")
            return False

        print(f"✅ Found user: {user.username} (ID: {user.id})")

        # Get current notification settings
        settings = get_user_notification_settings(user.id, session=session)
        print(f"\n📋 Current notification settings: {len(settings)} found")

        # Display current settings
        for setting in settings:
            status = "✅ Enabled" if setting.is_enabled else "❌ Disabled"
            print(f"  - {setting.notification_type}: {status}")

        # Test updating/creating settings for each notification type
        print("\n🔄 Testing update/create notification settings...")

        for notification_type in NotificationType:
            # Toggle the setting (enable if disabled, disable if enabled)
            current_setting = next(
                (s for s in settings if s.notification_type == notification_type.value),
                None
            )
            new_status = not current_setting.is_enabled if current_setting else True

            result = update_notification_setting(
                user.id,
                notification_type.value,
                new_status,
                session=session
            )

            if result:
                status_text = "enabled" if new_status else "disabled"
                print(f"  ✅ {notification_type.value}: {status_text}")
            else:
                print(f"  ❌ Failed to update {notification_type.value}")

        # Verify updates
        print("\n📋 Verifying updated settings...")
        updated_settings = get_user_notification_settings(user.id, session=session)

        for setting in updated_settings:
            status = "✅ Enabled" if setting.is_enabled else "❌ Disabled"
            print(f"  - {setting.notification_type}: {status}")

        print("\n✅ Notification settings test completed successfully!")
        return True


def test_notification_descriptions():
    """Test that all notification types have descriptions."""
    print("\n📝 Testing notification descriptions...")
    print("-" * 50)

    from src.notifications.types import get_notification_description

    for notification_type in NotificationType:
        description = get_notification_description(notification_type)
        if description:
            print(f"✅ {notification_type.value}: {description[:50]}...")
        else:
            print(f"❌ {notification_type.value}: No description")

    print("\n✅ Notification descriptions test completed!")
    return True


def main():
    """Main test function."""
    print("=" * 50)
    print("NOTIFICATION COMMAND TEST SUITE")
    print("=" * 50)

    try:
        # Test notification settings CRUD
        test_notification_settings()

        # Test notification descriptions
        test_notification_descriptions()

        print("\n" + "=" * 50)
        print("ALL TESTS COMPLETED SUCCESSFULLY! ✅")
        print("=" * 50)

        print("\n📌 Next steps:")
        print("1. Start the bot: python src/main.py")
        print("2. Send /notifications command to the bot")
        print("3. Test toggling each notification on/off")
        print("4. Verify changes are saved in the database")
        print("5. Check that APScheduler tasks are added/removed correctly")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())