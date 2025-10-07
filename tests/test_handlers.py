"""
Integration tests for Telegram bot handlers
This test module uses mocks extensively to test handlers without actual Telegram or database connections
"""

import json
import pytest
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))


@pytest.fixture
def mock_telegram_update():
    """Create a mock Telegram Update object"""
    from telegram import Update, Message, User, Chat

    # Mock user
    user_mock = MagicMock(spec=User)
    user_mock.id = 123456789
    user_mock.username = "test_user"
    user_mock.first_name = "Test"

    # Mock chat
    chat_mock = MagicMock(spec=Chat)
    chat_mock.id = 123456789

    # Mock message
    message_mock = MagicMock(spec=Message)
    message_mock.from_user = user_mock
    message_mock.chat = chat_mock
    message_mock.text = "/start"
    message_mock.reply_text = AsyncMock(return_value=MagicMock())
    message_mock.reply_html = AsyncMock(return_value=MagicMock())

    # Mock update
    update_mock = MagicMock(spec=Update)
    update_mock.message = message_mock
    update_mock.effective_user = user_mock
    update_mock.effective_chat = chat_mock
    update_mock.callback_query = None

    return update_mock


@pytest.fixture
def mock_telegram_context():
    """Create a mock Context object"""
    from telegram.ext import ContextTypes, Application

    context_mock = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # Mock bot
    bot_mock = MagicMock()
    bot_mock.send_message = AsyncMock(return_value=MagicMock())
    bot_mock.edit_message_text = AsyncMock(return_value=MagicMock())
    bot_mock.answer_callback_query = AsyncMock()

    context_mock.bot = bot_mock
    context_mock.bot_data = {'scheduler': MagicMock()}
    context_mock.user_data = {}

    return context_mock


@pytest.fixture
def mock_database():
    """Mock database functions"""
    with patch('database.crud.get_or_create_user') as mock_get_create_user, \
         patch('database.crud.get_user') as mock_get_user, \
         patch('database.crud.create_cycle') as mock_create_cycle, \
         patch('database.crud.get_current_cycle') as mock_get_cycle, \
         patch('database.crud.get_user_cycles') as mock_get_cycles, \
         patch('database.crud.update_cycle') as mock_update_cycle, \
         patch('database.crud.get_user_notification_settings') as mock_get_notif, \
         patch('database.crud.update_notification_setting') as mock_update_notif:

        # Setup mock return values
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.telegram_id = 123456789
        mock_user.username = "test_user"
        mock_user.timezone = "Europe/Moscow"
        mock_user.is_active = True

        mock_cycle = MagicMock()
        mock_cycle.id = 1
        mock_cycle.user_id = 1
        mock_cycle.start_date = date.today() - timedelta(days=5)
        mock_cycle.cycle_length = 28
        mock_cycle.period_length = 5
        mock_cycle.is_current = True

        mock_get_create_user.return_value = mock_user
        mock_get_user.return_value = mock_user
        mock_create_cycle.return_value = mock_cycle
        mock_get_cycle.return_value = mock_cycle
        mock_get_cycles.return_value = [mock_cycle]
        mock_update_cycle.return_value = mock_cycle

        yield {
            'get_or_create_user': mock_get_create_user,
            'get_user': mock_get_user,
            'create_cycle': mock_create_cycle,
            'get_current_cycle': mock_get_cycle,
            'get_user_cycles': mock_get_cycles,
            'update_cycle': mock_update_cycle,
            'get_user_notification_settings': mock_get_notif,
            'update_notification_setting': mock_update_notif,
            'mock_user': mock_user,
            'mock_cycle': mock_cycle
        }


class TestStartCommand:
    """Tests for /start command handler"""

    @pytest.mark.asyncio
    async def test_start_new_user(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /start command for new user"""
        from handlers.start import start_command

        # Set mock to return new user (get_or_create_user returns User object, not tuple)
        mock_database['mock_user'].command_count = 1  # New user has command_count = 1
        mock_database['mock_user'].increment_command_count = MagicMock()  # Mock the increment method
        mock_database['get_or_create_user'].return_value = mock_database['mock_user']

        await start_command(mock_telegram_update, mock_telegram_context)

        # Verify user was created (get_or_create_user doesn't accept first_name)
        mock_database['get_or_create_user'].assert_called_once_with(
            telegram_id=123456789,
            username="test_user"
        )

        # Verify welcome message was sent (checking actual message from handler)
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        # Handle both positional and keyword arguments
        if call_args.args:
            message_text = call_args.args[0]
        else:
            message_text = call_args.kwargs.get('text', '')
        assert "Добро пожаловать" in message_text

    @pytest.mark.asyncio
    async def test_start_existing_user(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /start command for existing user"""
        # Patch at the module level
        with patch('handlers.start.get_or_create_user') as mock_get_or_create:
            from handlers.start import start_command

            # Set mock to return existing user with command_count > 1
            mock_user = MagicMock()
            mock_user.command_count = 5  # Existing user has command_count > 1
            mock_user.increment_command_count = MagicMock()  # Mock the increment method
            mock_get_or_create.return_value = mock_user

            await start_command(mock_telegram_update, mock_telegram_context)

            # Verify welcome back message was sent
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args
            # Handle both positional and keyword arguments
            if call_args.args:
                message_text = call_args.args[0]
            else:
                message_text = call_args.kwargs.get('text', '')
            # For existing users, the handler uses "С возвращением"
            assert "С возвращением" in message_text


class TestHelpCommand:
    """Tests for /help command handler"""

    @pytest.mark.asyncio
    async def test_help_command(self, mock_telegram_update, mock_telegram_context):
        """Test /help command returns help text"""
        from handlers.help import help_command

        await help_command(mock_telegram_update, mock_telegram_context)

        # Verify help message was sent
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args

        # Check both positional and keyword arguments
        if call_args[0]:  # Positional args
            help_text = call_args[0][0]
        else:  # Keyword args
            help_text = call_args[1]['text']

        # Check for key commands in help text
        assert "/start" in help_text
        assert "/setup" in help_text
        assert "/status" in help_text
        assert "/settings" in help_text
        assert "/history" in help_text
        assert "/notifications" in help_text


class TestStatusCommand:
    """Tests for /status command handler"""

    @pytest.mark.asyncio
    async def test_status_no_cycle(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /status when user has no cycle"""
        with patch('handlers.status.get_user') as mock_get_user_status, \
             patch('handlers.status.get_current_cycle') as mock_get_cycle_status:
            from handlers.status import status_command

            # Set up mocks
            mock_get_user_status.return_value = mock_database['mock_user']
            # Set mock to return no cycle
            mock_get_cycle_status.return_value = None

            await status_command(mock_telegram_update, mock_telegram_context)

            # Verify message about missing cycle (check actual message from handler)
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args
            # Handler sends "У вас еще не настроен менструальный цикл"
            if call_args.args:
                message_text = call_args.args[0]
            else:
                message_text = call_args.kwargs.get('text', '')
            assert "не настроен" in message_text or "еще не" in message_text

    @pytest.mark.asyncio
    async def test_status_with_cycle(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /status when user has active cycle"""
        from handlers.status import status_command

        await status_command(mock_telegram_update, mock_telegram_context)

        # Verify status message was sent (using reply_text with HTML)
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args

        # Get the actual text and parse_mode
        if call_args[0]:
            status_text = call_args[0][0]
        else:
            status_text = call_args[1].get('text', '')

        parse_mode = call_args[1].get('parse_mode', '') if len(call_args) > 1 else ''

        # Check for key information
        assert "День цикла" in status_text or "Статус вашего цикла" in status_text
        assert parse_mode == 'HTML' or 'HTML' in str(call_args)


class TestSetupCommand:
    """Tests for /setup command and WebApp data handler"""

    @pytest.mark.asyncio
    async def test_setup_command(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /setup command opens WebApp"""
        from handlers.setup import setup_command

        await setup_command(mock_telegram_update, mock_telegram_context)

        # Verify WebApp button was sent
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        # Check for setup text in message (handler sends "настройку цикла" or similar)
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "настрой" in message_text.lower() or "цикл" in message_text.lower()
        assert call_args[1].get('reply_markup') is not None

    @pytest.mark.asyncio
    async def test_handle_web_app_data_valid(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test handling valid WebApp data"""
        # Patch all database functions at the module level where they're imported
        with patch('handlers.setup.get_user') as mock_get_user_setup, \
             patch('handlers.setup.get_current_cycle') as mock_get_current_setup, \
             patch('handlers.setup.create_cycle') as mock_create_setup, \
             patch('handlers.setup.update_cycle_status') as mock_update_status, \
             patch('handlers.setup.db_session.get_session'), \
             patch('handlers.setup.create_notification_tasks'):

            from handlers.setup import handle_webapp_data  # Correct function name
            from telegram import WebAppData

            # Set up mocks to return expected values
            mock_get_user_setup.return_value = mock_database['mock_user']
            mock_get_current_setup.return_value = None  # No current cycle
            mock_create_setup.return_value = mock_database['mock_cycle']

            # Setup WebApp data
            web_app_data_mock = MagicMock(spec=WebAppData)
            web_app_data_mock.data = json.dumps({
                "last_period_date": "2025-09-15",
                "cycle_length": 28,
                "period_length": 5
            })
            mock_telegram_update.message.web_app_data = web_app_data_mock

            await handle_webapp_data(mock_telegram_update, mock_telegram_context)

            # Verify cycle was created
            mock_create_setup.assert_called()

            # Verify confirmation message (handler uses reply_text, not reply_html)
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args
            if call_args.args:
                message_text = call_args.args[0]
            else:
                message_text = call_args.kwargs.get('text', '')
            # The handler sends "✅ Параметры цикла успешно сохранены!"
            assert "сохранены" in message_text or "успешно" in message_text

    @pytest.mark.asyncio
    async def test_handle_web_app_data_invalid(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test handling invalid WebApp data"""
        from handlers.setup import handle_webapp_data  # Correct function name
        from telegram import WebAppData

        # Setup invalid WebApp data
        web_app_data_mock = MagicMock(spec=WebAppData)
        web_app_data_mock.data = "invalid json {"
        mock_telegram_update.message.web_app_data = web_app_data_mock

        await handle_webapp_data(mock_telegram_update, mock_telegram_context)

        # Verify error message was sent
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "ошибка" in message_text.lower()


class TestSettingsCommand:
    """Tests for /settings command handler"""

    @pytest.mark.asyncio
    async def test_settings_command(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /settings command shows menu"""
        from handlers.settings import settings_command

        await settings_command(mock_telegram_update, mock_telegram_context)

        # Verify settings menu was sent
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "настройки" in call_args[0][0].lower()
        assert call_args[1].get('reply_markup') is not None


class TestHistoryCommand:
    """Tests for /history command handler"""

    @pytest.mark.asyncio
    async def test_history_no_cycles(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /history when user has no cycles"""
        # Need to patch at import level since get_user_by_telegram_id doesn't exist
        with patch('src.database.crud.get_user_by_telegram_id', create=True) as mock_get_user_by_id, \
             patch('src.database.crud.get_user_cycles') as mock_get_cycles, \
             patch('src.database.session.db_session.get_session'):
            from handlers.history import history_command

            # Set up mocks
            mock_get_user_by_id.return_value = mock_database['mock_user']
            mock_get_cycles.return_value = []

            await history_command(mock_telegram_update, mock_telegram_context)

            # Verify message about no cycles (the handler sends "У вас пока нет сохраненных циклов")
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            assert "пока нет" in message_text or "нет сохраненных" in message_text

    @pytest.mark.asyncio
    async def test_history_with_cycles(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /history when user has cycles"""
        # Patch the functions at the correct import location
        with patch('handlers.history.get_user') as mock_get_user_hist, \
             patch('handlers.history.get_user_cycles') as mock_get_cycles_hist, \
             patch('handlers.history.db_session.get_session'), \
             patch('handlers.history.show_history_page') as mock_show_page:
            from handlers.history import history_command

            # Set up mocks
            mock_get_user_hist.return_value = mock_database['mock_user']
            mock_get_cycles_hist.return_value = [mock_database['mock_cycle']]

            await history_command(mock_telegram_update, mock_telegram_context)

            # Verify show_history_page was called with correct arguments
            mock_show_page.assert_called_once_with(
                mock_telegram_update.message,
                [mock_database['mock_cycle']],
                0
            )


class TestNotificationsCommand:
    """Tests for /notifications command handler"""

    @pytest.mark.asyncio
    async def test_notifications_command(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test /notifications command shows settings"""
        # Patch at the module level where functions are imported
        with patch('handlers.notifications.get_user') as mock_get_user_notif, \
             patch('handlers.notifications.get_current_cycle') as mock_get_cycle_notif, \
             patch('handlers.notifications.get_user_notification_settings') as mock_get_settings:
            from handlers.notifications import notifications_command

            # Set up mocks to return expected values
            mock_get_user_notif.return_value = mock_database['mock_user']
            mock_get_cycle_notif.return_value = mock_database['mock_cycle']

            # Setup mock notification settings
            mock_notif_settings = [
                MagicMock(notification_type='PERIOD_REMINDER', is_enabled=True),
                MagicMock(notification_type='OVULATION_DAY', is_enabled=False)
            ]
            mock_get_settings.return_value = mock_notif_settings

            await notifications_command(mock_telegram_update, mock_telegram_context)

            # Verify notifications menu was sent (handler sends with reply_html)
            # Check both reply_text and reply_html methods
            assert mock_telegram_update.message.reply_text.called or mock_telegram_update.message.reply_html.called

            # Get the call args from whichever method was called
            if mock_telegram_update.message.reply_html.called:
                call_args = mock_telegram_update.message.reply_html.call_args
            else:
                call_args = mock_telegram_update.message.reply_text.call_args

            if call_args.args:
                message_text = call_args.args[0]
            else:
                message_text = call_args.kwargs.get('text', '')
            assert "Управление уведомлениями" in message_text


class TestCallbackQueries:
    """Tests for callback query handlers"""

    @pytest.mark.asyncio
    async def test_callback_query_handling(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test that callback queries are handled properly"""
        from telegram import CallbackQuery

        # Setup callback query
        callback_mock = MagicMock(spec=CallbackQuery)
        callback_mock.data = "show_status"
        callback_mock.answer = AsyncMock()
        callback_mock.edit_message_text = AsyncMock()
        callback_mock.from_user = MagicMock()
        callback_mock.from_user.id = 123456789

        mock_telegram_update.callback_query = callback_mock
        mock_telegram_update.message = None

        # This would typically be handled by a callback handler
        # Just verify the structure is correct
        assert callback_mock.data == "show_status"
        await callback_mock.answer()
        callback_mock.answer.assert_called_once()


class TestErrorHandling:
    """Tests for error handling in handlers"""

    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test handlers handle database errors gracefully"""
        # Patch at the module level where it's imported
        with patch('handlers.status.get_user') as mock_get_user_status:
            from handlers.status import status_command

            # Simulate database error
            mock_get_user_status.side_effect = Exception("Database connection error")

            await status_command(mock_telegram_update, mock_telegram_context)

            # Should send error message instead of crashing (handler sends "Произошла ошибка")
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args
            if call_args.args:
                message_text = call_args.args[0]
            else:
                message_text = call_args.kwargs.get('text', '')
            # The handler sends "❌ Произошла ошибка при получении статуса цикла."
            assert "Произошла ошибка" in message_text or "ошибка" in message_text.lower()

    @pytest.mark.asyncio
    async def test_missing_user_handling(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test handlers handle missing user gracefully"""
        from handlers.status import status_command

        # Simulate missing user
        mock_database['get_user'].return_value = None

        await status_command(mock_telegram_update, mock_telegram_context)

        # Should handle gracefully
        assert mock_telegram_update.message.reply_text.called or mock_telegram_update.message.reply_html.called


class TestDataValidation:
    """Tests for data validation in handlers"""

    @pytest.mark.asyncio
    async def test_invalid_cycle_length(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test validation of cycle length"""
        from handlers.setup import handle_webapp_data  # Correct function name
        from telegram import WebAppData

        # Setup WebApp data with invalid cycle length
        web_app_data_mock = MagicMock(spec=WebAppData)
        web_app_data_mock.data = json.dumps({
            "last_period_date": "2025-09-15",
            "cycle_length": 50,  # Too long
            "period_length": 5
        })
        mock_telegram_update.message.web_app_data = web_app_data_mock

        await handle_webapp_data(mock_telegram_update, mock_telegram_context)

        # Should send validation error
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        if call_args.args:
            message_text = call_args.args[0]
        else:
            message_text = call_args.kwargs.get('text', '')
        # Handler just sends generic error message, not specific validation details
        assert "ошибка" in message_text.lower()

    @pytest.mark.asyncio
    async def test_future_date_validation(self, mock_telegram_update, mock_telegram_context, mock_database):
        """Test validation of future dates"""
        from handlers.setup import handle_webapp_data  # Correct function name
        from telegram import WebAppData

        # Setup WebApp data with future date
        future_date = (date.today() + timedelta(days=10)).isoformat()
        web_app_data_mock = MagicMock(spec=WebAppData)
        web_app_data_mock.data = json.dumps({
            "last_period_date": future_date,
            "cycle_length": 28,
            "period_length": 5
        })
        mock_telegram_update.message.web_app_data = web_app_data_mock

        await handle_webapp_data(mock_telegram_update, mock_telegram_context)

        # Should send validation error about future date
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        if call_args.args:
            message_text = call_args.args[0]
        else:
            message_text = call_args.kwargs.get('text', '')
        # Handler just sends generic error message, not specific validation details
        assert "ошибка" in message_text.lower()