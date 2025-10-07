# Ovulo - Telegram Bot for Menstrual Cycle Tracking

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Telegram Bot API](https://img.shields.io/badge/python--telegram--bot-20.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-blue)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

Ovulo is a Telegram bot designed to help users track their menstrual cycles, predict future periods, and receive timely notifications. The bot provides a user-friendly interface with both command-based and WebApp-based setup options.

## Features

### Core Functionality
- 📱 **Easy Setup via WebApp** - Interactive web interface for initial cycle configuration
- 📊 **Cycle Tracking** - Track menstrual cycles with customizable cycle and period lengths
- 🔔 **Smart Notifications** - Automated reminders for upcoming periods and ovulation
- 📅 **History Tracking** - View and manage past cycles
- ⚙️ **Flexible Settings** - Adjust cycle parameters, timezone, and notification preferences
- 🌍 **Internationalization Ready** - Support for multiple languages (Russian by default)
- 🔒 **Privacy-First** - GDPR compliant with data export and deletion options

### Technical Features
- 🐳 **Docker Support** - Easy deployment with Docker Compose
- 🗄️ **PostgreSQL Database** - Reliable data storage with automatic migrations
- 📈 **Admin Statistics** - Built-in analytics for bot administrators
- 🔄 **Backup & Restore** - Automated database backup scripts
- 🚀 **CI/CD Ready** - GitHub Actions workflow for automated testing and deployment
- 📝 **Comprehensive Logging** - Structured logging for debugging and monitoring

## Technology Stack

- **Language**: Python 3.10+
- **Bot Framework**: python-telegram-bot 20.x
- **Database**: PostgreSQL 13+
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Task Scheduling**: APScheduler
- **Containerization**: Docker & Docker Compose
- **Web Interface**: HTML5 + Telegram WebApp API

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 13 or higher
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ovulo.git
cd ovulo
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token
ADMIN_TELEGRAM_ID=your_telegram_id

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ovulo_dev
POSTGRES_USER=ovulo_user
POSTGRES_PASSWORD=secure_password

# WebApp Configuration
WEBAPP_URL=https://your-domain.com
```

5. **Initialize database**
```bash
# Create database
psql -U postgres -c "CREATE DATABASE ovulo_dev;"
psql -U postgres -c "CREATE USER ovulo_user WITH PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE ovulo_dev TO ovulo_user;"

# Run migrations
alembic upgrade head
```

6. **Run the bot**
```bash
python src/main.py
```

### Docker Deployment

1. **Clone and configure**
```bash
git clone https://github.com/yourusername/ovulo.git
cd ovulo
cp .env.example .env
# Edit .env with your configuration
```

2. **Build and run with Docker Compose**
```bash
docker compose up -d
```

3. **Check logs**
```bash
docker compose logs -f bot
```

## Usage

### Bot Commands

- `/start` - Initialize bot and show welcome message
- `/setup` - Open WebApp for cycle configuration
- `/status` - View current cycle status and predictions
- `/history` - View cycle history
- `/settings` - Configure bot settings
- `/notifications` - Manage notification preferences
- `/help` - Show help message
- `/export_data` - Export your data (GDPR)
- `/delete_data` - Delete all your data (GDPR)
- `/admin_stats` - Show bot statistics (admin only)

### Initial Setup Process

1. Start the bot with `/start`
2. Click "Setup Cycle" button or use `/setup`
3. In the WebApp interface:
   - Select your last period start date
   - Set your average cycle length (21-40 days)
   - Set your average period length (1-10 days)
   - Save configuration
4. The bot will automatically calculate and schedule notifications

### Notification Types

- **Period Reminder** - 3 days before expected period
- **Ovulation Reminder** - During fertile window
- **Period Start** - On expected period start date

## Project Structure

```
Ovulo/
├── src/
│   ├── bot/            # Bot initialization and configuration
│   ├── handlers/       # Command and message handlers
│   ├── models/         # SQLAlchemy database models
│   ├── database/       # Database connection and CRUD operations
│   ├── notifications/  # Notification scheduling system
│   ├── utils/          # Utility functions and helpers
│   ├── webapp/         # WebApp frontend files
│   └── main.py         # Application entry point
├── migrations/         # Alembic database migrations
├── scripts/           # Utility scripts (backup, restore)
├── documentation/     # Additional documentation
├── tests/            # Test suite
├── docker-compose.yml # Docker Compose configuration
├── Dockerfile        # Docker image definition
├── requirements.txt  # Python dependencies
├── alembic.ini      # Alembic configuration
└── .env.example     # Environment variables template
```

## Database Backup and Restore

### Automated Backup
```bash
# Create backup
./scripts/backup_db.sh

# Schedule daily backups with cron
crontab -e
# Add: 0 2 * * * /path/to/scripts/backup_db.sh
```

### Restore from Backup
```bash
# Restore database
./scripts/restore_db.sh backups/backup_file.sql.gz
```

## Development

### Running Tests
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

### Code Style
```bash
# Format code
black src/
isort src/

# Lint code
flake8 src/
pylint src/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation as needed
- Keep commits atomic and well-described
- Ensure all tests pass before submitting PR

## Security

- Never commit `.env` files or secrets
- Use environment variables for sensitive data
- Regular security updates for dependencies
- Input validation and sanitization
- Rate limiting for API endpoints
- Encrypted database connections in production

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Create an [Issue](https://github.com/yourusername/ovulo/issues) for bug reports
- Join our [Telegram Group](https://t.me/ovulo_support) for discussions
- Check [Documentation](documentation/) for detailed guides

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling
- All contributors and users of the bot

---

Made with ❤️ for women's health tracking