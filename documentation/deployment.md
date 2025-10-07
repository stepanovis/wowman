# Ovulo Bot Deployment Guide

This guide provides comprehensive instructions for deploying the Ovulo Telegram bot in production using Docker.

## Table of Contents

- [Server Requirements](#server-requirements)
- [Prerequisites Installation](#prerequisites-installation)
- [Environment Setup](#environment-setup)
- [Deployment Process](#deployment-process)
- [Bot Management](#bot-management)
- [Database Backup and Restore](#database-backup-and-restore)
- [Monitoring and Logs](#monitoring-and-logs)
- [Updating the Bot](#updating-the-bot)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

## Server Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Any Linux with Docker support
- **RAM**: 1GB minimum, 2GB recommended
- **CPU**: 1 vCPU minimum, 2 vCPU recommended
- **Storage**: 10GB minimum (for OS, Docker images, database, and logs)
- **Network**: Stable internet connection with outbound HTTPS access

### Recommended Requirements
- **RAM**: 4GB
- **CPU**: 2-4 vCPU
- **Storage**: 20GB+ SSD
- **Backup**: Regular automated backups configured

## Prerequisites Installation

### 1. Install Docker

#### Ubuntu/Debian:
```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker --version
```

#### CentOS/RHEL/Fedora:
```bash
# Install required packages
sudo yum install -y yum-utils

# Set up repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
```

### 2. Install Docker Compose

Docker Compose is included with Docker Engine as a plugin. Verify installation:

```bash
docker compose version
```

If not available, install standalone version:

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 3. Configure Docker (Optional)

Add your user to the docker group to run Docker without sudo:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Environment Setup

### 1. Clone the Repository

```bash
# Clone from your repository
git clone https://github.com/yourusername/ovulo-bot.git
cd ovulo-bot
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

Required configuration in `.env`:

```env
# Bot Configuration
BOT_TOKEN=your_bot_token_from_botfather

# Database Configuration
DB_HOST=postgres  # Use 'postgres' for Docker
DB_PORT=5432
DB_NAME=ovulo
DB_USER=postgres
DB_PASSWORD=your_secure_password_here  # Use strong password!

# Logging
LOG_LEVEL=INFO
ENV=production

# Optional: Admin notifications
ADMIN_TELEGRAM_ID=your_telegram_id  # Get from @userinfobot

# Timezone
TZ=Europe/Moscow
```

### 3. Configure WebApp (if using)

For production WebApp:
1. Deploy HTML files to HTTPS server
2. Set `WEBAPP_URL` in `.env`:
```env
WEBAPP_URL=https://your-domain.com/webapp/setup_form.html
```

## Deployment Process

### 1. Build and Start Services

```bash
# Build the Docker image
docker compose build

# Start all services in detached mode
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f bot
```

### 2. Verify Deployment

Check that all services are running:

```bash
# Check container status
docker ps

# Check bot logs
docker compose logs bot --tail 100

# Check database connection
docker compose exec postgres psql -U postgres -d ovulo -c "\dt"
```

Test the bot:
1. Open Telegram
2. Search for your bot: @YourBotName
3. Send `/start` command
4. Verify bot responds

## Bot Management

### Starting and Stopping

```bash
# Stop all services
docker compose down

# Start services
docker compose up -d

# Restart specific service
docker compose restart bot

# Stop without removing containers
docker compose stop

# Start stopped containers
docker compose start
```

### Viewing Logs

```bash
# View all logs
docker compose logs

# View bot logs (last 100 lines)
docker compose logs bot --tail 100

# Follow logs in real-time
docker compose logs -f bot

# View logs with timestamps
docker compose logs -t bot
```

### Executing Commands

```bash
# Open shell in bot container
docker compose exec bot /bin/bash

# Run Python shell
docker compose exec bot python

# Check database migrations
docker compose exec bot alembic current
```

## Database Backup and Restore

### Using Provided Scripts

The project includes professional backup and restore scripts in the `scripts/` directory that work both locally and with Docker.

#### Backup Script (`scripts/backup_db.sh`)

**Features:**
- Automatic environment variable loading from `.env`
- Support for both local and Docker container databases
- Automatic compression with gzip
- Retention policy (keeps last 10 backups)
- Detailed logging and error handling

**Usage Examples:**

```bash
# Basic backup using .env configuration
./scripts/backup_db.sh

# Backup from Docker container
./scripts/backup_db.sh -c ovulo-postgres

# Backup with custom directory
./scripts/backup_db.sh -d /path/to/backups

# Backup with custom database settings
./scripts/backup_db.sh --host localhost --port 5433 --db ovulo_prod

# Show help
./scripts/backup_db.sh --help
```

#### Restore Script (`scripts/restore_db.sh`)

**Features:**
- Automatic decompression of `.gz` files
- Safety confirmation prompt (can be bypassed with `-f`)
- Database recreation for clean restore
- Automatic migration execution after restore
- Support for both local and Docker databases

**Usage Examples:**

```bash
# Restore from backup file
./scripts/restore_db.sh backups/ovulo_backup_20240101_120000.sql.gz

# Restore to Docker container
./scripts/restore_db.sh -c ovulo-postgres backups/backup.sql.gz

# Force restore without confirmation
./scripts/restore_db.sh -f backups/backup.sql.gz

# Restore with custom settings
./scripts/restore_db.sh --host localhost --port 5433 backup.sql

# Show help
./scripts/restore_db.sh --help
```

### Automated Backups with Cron

Create a cron job for automatic daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/project/scripts/backup_db.sh >> /var/log/ovulo_backup.log 2>&1

# Or for Docker container backup
0 2 * * * /path/to/project/scripts/backup_db.sh -c ovulo-postgres >> /var/log/ovulo_backup.log 2>&1
```

### Manual Docker Commands (Alternative)

If you prefer using Docker commands directly:

```bash
# Backup database
docker compose exec postgres pg_dump -U postgres ovulo > ovulo_backup_$(date +%Y%m%d).sql

# Backup with compression
docker compose exec postgres pg_dump -U postgres ovulo | gzip > ovulo_backup_$(date +%Y%m%d).sql.gz

# Backup Docker volumes
docker run --rm -v ovulo_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data_backup_$(date +%Y%m%d).tar.gz /data
```

### Restore from Docker Backup

```bash
# Stop bot service (keep database running)
docker compose stop bot

# Restore from SQL backup
docker compose exec -T postgres psql -U postgres ovulo < ovulo_backup_20240101.sql

# Or restore from compressed backup
gunzip -c ovulo_backup_20240101.sql.gz | docker compose exec -T postgres psql -U postgres ovulo

# Restart bot
docker compose start bot
```

### Best Practices

1. **Regular Backups**: Set up automated daily backups using cron
2. **Offsite Storage**: Copy backups to external storage or cloud (S3, Google Cloud Storage)
3. **Test Restores**: Periodically test restore process on a staging environment
4. **Monitor Backup Jobs**: Check backup logs regularly for failures
5. **Retention Policy**: Keep daily backups for 7 days, weekly for a month, monthly for a year

## Monitoring and Logs

### Log Management

Configure log rotation in `docker-compose.yml` (already included):

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
```

### Monitoring Commands

```bash
# Check resource usage
docker stats

# Check disk usage
docker system df

# View container details
docker compose ps -a

# Health check
docker compose exec bot curl -f http://localhost:8080/health || echo "Health check failed"
```

### Setting Up Monitoring (Optional)

For production, consider using:
- **Prometheus** + **Grafana** for metrics
- **ELK Stack** (Elasticsearch, Logstash, Kibana) for log aggregation
- **Uptime monitoring** services (UptimeRobot, Pingdom)

## Updating the Bot

### 1. Pull Latest Changes

```bash
# Stop services
docker compose down

# Pull latest code
git pull origin main

# Review changes in .env.example
diff .env .env.example
```

### 2. Update Environment

If there are new environment variables:

```bash
# Edit environment file
nano .env
# Add any new required variables
```

### 3. Rebuild and Deploy

```bash
# Rebuild image with latest code
docker compose build --no-cache

# Run database migrations
docker compose run --rm bot alembic upgrade head

# Start services
docker compose up -d

# Check logs
docker compose logs -f bot
```

### 4. Zero-Downtime Update (Advanced)

For zero-downtime updates:

```bash
# Build new image with tag
docker compose build bot
docker tag ovulo-bot:latest ovulo-bot:backup

# Start new container alongside old one
docker compose up -d --no-deps --scale bot=2 bot

# Wait for new container to be healthy
sleep 30

# Remove old container
docker compose up -d --no-deps --scale bot=1 bot
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Bot doesn't respond

**Check bot token:**
```bash
docker compose exec bot python -c "import os; print('Token set:', bool(os.getenv('BOT_TOKEN')))"
```

**Check logs:**
```bash
docker compose logs bot --tail 50
```

#### 2. Database connection errors

**Check PostgreSQL status:**
```bash
docker compose ps postgres
docker compose logs postgres --tail 20
```

**Test connection:**
```bash
docker compose exec postgres pg_isready -U postgres
```

#### 3. Migration errors

**Check current migration:**
```bash
docker compose exec bot alembic current
```

**Reset migrations (CAUTION: Data loss!):**
```bash
docker compose exec bot alembic downgrade base
docker compose exec bot alembic upgrade head
```

#### 4. High memory usage

**Check memory:**
```bash
docker stats --no-stream
```

**Limit memory in docker-compose.yml:**
```yaml
services:
  bot:
    mem_limit: 512m
    mem_reservation: 256m
```

#### 5. Container keeps restarting

**Check exit code:**
```bash
docker compose ps -a
```

**View detailed logs:**
```bash
docker compose logs bot --tail 100
```

**Debug interactively:**
```bash
docker compose run --rm bot /bin/bash
```

### Debug Mode

Enable debug logging:

```bash
# Edit .env
LOG_LEVEL=DEBUG
ENV=development

# Restart bot
docker compose restart bot

# View debug logs
docker compose logs -f bot
```

## Security Best Practices

### 1. Environment Variables

- **Never commit `.env` to version control**
- Use strong passwords for database
- Rotate bot token if compromised
- Store sensitive data in secrets management system (e.g., HashiCorp Vault)

### 2. Network Security

```bash
# Configure firewall (UFW example)
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 443/tcp # HTTPS (if running webapp)
sudo ufw enable
```

### 3. Docker Security

```yaml
# Add security options to docker-compose.yml
services:
  bot:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

### 4. Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker compose pull
docker compose up -d

# Remove unused images
docker image prune -a
```

### 5. SSL/TLS for WebApp

If hosting WebApp, use HTTPS with valid SSL certificate:
- Use Let's Encrypt for free certificates
- Configure nginx as reverse proxy
- Enable HSTS headers

### 6. Backup Encryption

Encrypt backups before storing:

```bash
# Encrypt backup
openssl enc -aes-256-cbc -salt -in backup.sql -out backup.sql.enc -k password

# Decrypt backup
openssl enc -d -aes-256-cbc -in backup.sql.enc -out backup.sql -k password
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Python Telegram Bot Documentation](https://python-telegram-bot.readthedocs.io/)

## Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review bot logs: `docker compose logs bot`
3. Check GitHub Issues
4. Contact the development team

---

**Last Updated**: October 2024
**Version**: 1.0.0