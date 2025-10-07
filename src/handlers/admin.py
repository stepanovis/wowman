"""
Admin commands handler for bot owner.
"""

import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy import func, and_

from utils.logger import get_logger
from database.session import db_session
from database import crud
from models.user import User
from models.cycle import Cycle
from models.notification_log import NotificationLog

# Set up logging
logger = get_logger(__name__)


async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show bot statistics for the admin.
    Only accessible to the bot owner specified in ADMIN_TELEGRAM_ID environment variable.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    try:
        telegram_id = update.effective_user.id

        # Check if user is admin
        admin_id = os.getenv('ADMIN_TELEGRAM_ID')
        if not admin_id or str(telegram_id) != admin_id:
            await update.message.reply_text(
                "❌ У вас нет доступа к этой команде.",
                parse_mode='HTML'
            )
            logger.warning(f"Unauthorized access to /admin_stats by user {telegram_id}")
            return

        # Gather statistics
        with db_session.get_session() as db:
            # Total users
            total_users = db.query(func.count(User.id)).scalar()

            # Active users
            active_users = db.query(func.count(User.id)).filter(
                User.is_active == True
            ).scalar()

            # Users active in last 7 days
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            active_7d = db.query(func.count(User.id)).filter(
                and_(
                    User.last_active_at >= seven_days_ago,
                    User.is_active == True
                )
            ).scalar()

            # Users active in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_30d = db.query(func.count(User.id)).filter(
                and_(
                    User.last_active_at >= thirty_days_ago,
                    User.is_active == True
                )
            ).scalar()

            # Total cycles
            total_cycles = db.query(func.count(Cycle.id)).scalar()

            # Active cycles (current)
            active_cycles = db.query(func.count(Cycle.id)).filter(
                Cycle.is_current == True
            ).scalar()

            # Average cycle length (for all cycles)
            avg_cycle_length = db.query(func.avg(Cycle.cycle_length)).scalar()
            if avg_cycle_length:
                avg_cycle_length = round(avg_cycle_length, 1)
            else:
                avg_cycle_length = 0

            # Average period length
            avg_period_length = db.query(func.avg(Cycle.period_length)).scalar()
            if avg_period_length:
                avg_period_length = round(avg_period_length, 1)
            else:
                avg_period_length = 0

            # Total commands executed (sum of all users' command counts)
            total_commands = db.query(func.sum(User.commands_count)).scalar() or 0

            # Notifications sent in last 24 hours
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            notifications_24h = db.query(func.count(NotificationLog.id)).filter(
                and_(
                    NotificationLog.sent_at >= one_day_ago,
                    NotificationLog.status == 'sent'
                )
            ).scalar()

            # Failed notifications in last 24 hours
            failed_notifications_24h = db.query(func.count(NotificationLog.id)).filter(
                and_(
                    NotificationLog.sent_at >= one_day_ago,
                    NotificationLog.status == 'failed'
                )
            ).scalar()

            # Most active users (top 5 by command count)
            top_users = db.query(
                User.username,
                User.telegram_id,
                User.commands_count
            ).filter(
                User.commands_count > 0
            ).order_by(
                User.commands_count.desc()
            ).limit(5).all()

        # Format statistics message
        stats_message = f"""
📊 <b>Статистика бота Ovulo</b>

👥 <b>Пользователи:</b>
• Всего пользователей: <code>{total_users}</code>
• Активных: <code>{active_users}</code>
• Активных за 7 дней: <code>{active_7d}</code>
• Активных за 30 дней: <code>{active_30d}</code>

🔄 <b>Циклы:</b>
• Всего циклов: <code>{total_cycles}</code>
• Активных циклов: <code>{active_cycles}</code>
• Средняя длина цикла: <code>{avg_cycle_length}</code> дней
• Средняя длина менструации: <code>{avg_period_length}</code> дней

📈 <b>Активность:</b>
• Всего команд выполнено: <code>{total_commands}</code>
• Уведомлений за 24ч: <code>{notifications_24h}</code>
• Неудачных уведомлений за 24ч: <code>{failed_notifications_24h}</code>
"""

        # Add top users if any
        if top_users:
            stats_message += "\n🏆 <b>Топ активных пользователей:</b>\n"
            for i, (username, tid, count) in enumerate(top_users, 1):
                user_display = username if username else f"ID:{tid}"
                stats_message += f"{i}. {user_display}: <code>{count}</code> команд\n"

        # Add timestamp
        stats_message += f"\n⏱ <i>Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"

        await update.message.reply_text(stats_message, parse_mode='HTML')
        logger.info(f"Admin stats requested by user {telegram_id}")

    except Exception as e:
        logger.error(f"Error in admin_stats_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при получении статистики. Попробуйте позже.",
            parse_mode='HTML'
        )


def get_admin_handlers():
    """
    Get list of admin command handlers.

    Returns:
        list: List of CommandHandler objects for admin commands
    """
    return [
        CommandHandler("admin_stats", admin_stats_command),
    ]