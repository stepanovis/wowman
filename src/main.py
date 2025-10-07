#!/usr/bin/env python3
"""
Main entry point for the Ovulo Telegram bot.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()

# Configure structured logging
from utils.logger import setup_logging, get_logger

# Initialize logging configuration
setup_logging()

# Get logger for this module
logger = get_logger(__name__)

# Import bot module after path is set
from bot.bot import create_bot
# from database.session import init_database  # TODO: Fix import and uncomment when needed


def check_environment():
    """Check if all required environment variables are set."""
    # Try multiple possible token names
    token_present = os.getenv('BOT_TOKEN') or os.getenv('TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')

    missing_vars = []
    if not token_present:
        missing_vars.append('BOT_TOKEN')

    required_vars = ['DB_NAME', 'DB_USER']
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        return False

    return True


def init_database():
    """Initialize database connection and apply migrations if needed."""
    try:
        # TODO: Initialize database connection
        # TODO: Run alembic migrations
        logger.info("Database initialization placeholder - will be implemented later")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def main():
    """
    Main function to initialize and start the bot.
    """
    logger.info("=" * 50)
    logger.info("Starting Ovulo Telegram Bot")
    logger.info("=" * 50)

    # Check environment variables
    if not check_environment():
        sys.exit(1)

    webapp_server = None
    try:
        # Initialize database (placeholder for now)
        # asyncio.run(initialize_database())

        # Start WebApp server if in development mode and WEBAPP_URL is not set
        if not os.getenv('WEBAPP_URL') and os.getenv('WEBAPP_DEV', 'false').lower() == 'true':
            from webapp.server import WebAppServer
            webapp_server = WebAppServer(port=8080)
            webapp_server.start()
            logger.info("Development WebApp server started on port 8080")
            logger.info("For production, deploy HTML to HTTPS server and set WEBAPP_URL")

        # Create and configure the bot
        bot = create_bot()

        logger.info("Bot initialization complete. Starting polling...")
        logger.info("Press Ctrl+C to stop the bot")

        # Start the bot
        bot.run()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if webapp_server:
            webapp_server.stop()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 50)
        logger.info("Bot stopped by user")
        logger.info("=" * 50)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)