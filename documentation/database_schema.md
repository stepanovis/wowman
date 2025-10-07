# Схема базы данных Ovulo Bot

## Обзор

База данных спроектирована для хранения информации о пользователях, их менструальных циклах, настройках уведомлений и логах отправленных уведомлений.

## ER-диаграмма (текстовое представление)

```
┌─────────────────────────┐
│        users            │
├─────────────────────────┤
│ id (PK)                 │
│ telegram_id (UNIQUE)    │
│ username                │
│ timezone                │
│ created_at              │
│ is_active               │
│ last_active_at          │
│ commands_count          │
│ preferred_language      │
└─────────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────┐      ┌──────────────────────────────┐
│        cycles           │      │   notification_settings      │
├─────────────────────────┤      ├──────────────────────────────┤
│ id (PK)                 │      │ id (PK)                      │
│ user_id (FK) ───────────┼──────┤ user_id (FK)                 │
│ start_date              │      │ notification_type            │
│ cycle_length            │      │ is_enabled                   │
│ period_length           │      │ time_offset                  │
│ created_at              │      │ custom_time                  │
│ updated_at              │      │ created_at                   │
│ is_current              │      │ updated_at                   │
│ notes                   │      └──────────────────────────────┘
└─────────────────────────┘                      │
                                                 │ 1:N
                                                 ▼
                                   ┌──────────────────────────────┐
                                   │    notification_log          │
                                   ├──────────────────────────────┤
                                   │ id (PK)                      │
                                   │ user_id (FK)                 │
                                   │ notification_type            │
                                   │ scheduled_at                 │
                                   │ sent_at                      │
                                   │ status                       │
                                   │ error_message                │
                                   │ retry_count                  │
                                   │ created_at                   │
                                   └──────────────────────────────┘

                                   ┌──────────────────────────────┐
                                   │  apscheduler_jobs            │
                                   ├──────────────────────────────┤
                                   │ id (PK)                      │
                                   │ next_run_time                │
                                   │ job_state                    │
                                   └──────────────────────────────┘
```

## Описание таблиц

### 1. Таблица `users`

Хранит информацию о пользователях бота.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY, AUTO_INCREMENT |
| telegram_id | BIGINT | ID пользователя в Telegram | UNIQUE, NOT NULL, INDEX |
| username | VARCHAR(255) | Username пользователя в Telegram | NULL |
| timezone | VARCHAR(50) | Часовой пояс пользователя | DEFAULT 'Europe/Moscow' |
| created_at | TIMESTAMP | Дата и время регистрации | DEFAULT CURRENT_TIMESTAMP |
| is_active | BOOLEAN | Статус активности пользователя | DEFAULT TRUE |
| last_active_at | TIMESTAMP | Последняя активность | NULL |
| commands_count | INTEGER | Количество выполненных команд | DEFAULT 0 |
| preferred_language | VARCHAR(10) | Предпочтительный язык | DEFAULT 'ru' |

**Индексы:**
- `idx_users_telegram_id` на `telegram_id` для быстрого поиска
- `idx_users_is_active` на `is_active` для фильтрации активных пользователей
- `idx_users_created_at` на `created_at` для сортировки по дате регистрации

### 2. Таблица `cycles`

Хранит информацию о менструальных циклах пользователей.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY, AUTO_INCREMENT |
| user_id | INTEGER | ID пользователя | FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE |
| start_date | DATE | Дата начала цикла | NOT NULL |
| cycle_length | INTEGER | Длина цикла в днях | NOT NULL, CHECK (cycle_length BETWEEN 21 AND 40) |
| period_length | INTEGER | Длина месячных в днях | NOT NULL, CHECK (period_length BETWEEN 1 AND 10) |
| created_at | TIMESTAMP | Дата создания записи | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | Дата последнего обновления | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |
| is_current | BOOLEAN | Признак текущего активного цикла | DEFAULT FALSE |
| notes | TEXT | Заметки пользователя | NULL |

**Индексы:**
- `idx_cycles_user_id` на `user_id` для быстрого поиска циклов пользователя
- `idx_cycles_is_current` на `is_current` для быстрого поиска активного цикла
- `idx_cycles_start_date` на `start_date` для сортировки по дате
- Составной индекс `idx_cycles_user_current` на `(user_id, is_current)` для поиска активного цикла пользователя

**Ограничения:**
- Только один цикл может иметь `is_current = TRUE` для каждого пользователя (реализуется через триггер или логику приложения)

### 3. Таблица `notification_settings`

Хранит настройки уведомлений для каждого пользователя.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY, AUTO_INCREMENT |
| user_id | INTEGER | ID пользователя | FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE |
| notification_type | VARCHAR(50) | Тип уведомления | NOT NULL |
| is_enabled | BOOLEAN | Включено ли уведомление | DEFAULT TRUE |
| time_offset | INTEGER | Смещение времени в минутах | DEFAULT 0 |
| custom_time | TIME | Пользовательское время отправки | NULL |
| created_at | TIMESTAMP | Дата создания | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | Дата обновления | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

**Индексы:**
- Составной индекс `idx_notification_settings_user_type` на `(user_id, notification_type)` - UNIQUE
- `idx_notification_settings_is_enabled` на `is_enabled` для фильтрации активных уведомлений

**Типы уведомлений (notification_type):**
- `PERIOD_REMINDER` - напоминание о приближении месячных (за 2 дня)
- `PERIOD_START` - уведомление о начале месячных
- `FERTILE_WINDOW_START` - начало фертильного окна
- `OVULATION_DAY` - день овуляции
- `SAFE_PERIOD` - начало безопасного периода

### 4. Таблица `notification_log`

Логирует все отправленные (или попытки отправки) уведомления.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY, AUTO_INCREMENT |
| user_id | INTEGER | ID пользователя | FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE |
| notification_type | VARCHAR(50) | Тип уведомления | NOT NULL |
| scheduled_at | TIMESTAMP | Запланированное время отправки | NOT NULL |
| sent_at | TIMESTAMP | Фактическое время отправки | NULL |
| status | VARCHAR(20) | Статус отправки | NOT NULL |
| error_message | TEXT | Сообщение об ошибке | NULL |
| retry_count | INTEGER | Количество попыток отправки | DEFAULT 0 |
| created_at | TIMESTAMP | Дата создания записи | DEFAULT CURRENT_TIMESTAMP |

**Индексы:**
- `idx_notification_log_user_id` на `user_id`
- `idx_notification_log_status` на `status`
- `idx_notification_log_sent_at` на `sent_at`
- Составной индекс `idx_notification_log_user_type_date` на `(user_id, notification_type, sent_at)`

**Возможные статусы:**
- `SCHEDULED` - запланировано
- `SENT` - успешно отправлено
- `FAILED` - ошибка при отправке
- `RETRY` - повторная попытка
- `CANCELLED` - отменено

### 5. Таблица `apscheduler_jobs` (системная)

Таблица для хранения заданий APScheduler (создается автоматически).

| Поле | Тип | Описание |
|------|-----|----------|
| id | VARCHAR(191) | ID задания |
| next_run_time | DOUBLE | Время следующего запуска |
| job_state | BLOB | Сериализованное состояние задания |

## Связи между таблицами

1. **users → cycles** (1:N)
   - Один пользователь может иметь множество записей о циклах
   - При удалении пользователя удаляются все его циклы (CASCADE)

2. **users → notification_settings** (1:N)
   - Один пользователь имеет настройки для каждого типа уведомлений
   - При удалении пользователя удаляются все настройки (CASCADE)

3. **users → notification_log** (1:N)
   - Один пользователь может иметь множество записей в логе уведомлений
   - При удалении пользователя удаляются все записи лога (CASCADE)

## Оптимизации

### Индексы для производительности

1. **Частые запросы:**
   - Поиск пользователя по `telegram_id` - индекс на `users.telegram_id`
   - Поиск активного цикла пользователя - составной индекс на `cycles(user_id, is_current)`
   - Поиск настроек уведомлений - составной индекс на `notification_settings(user_id, notification_type)`
   - Фильтрация логов по статусу - индекс на `notification_log.status`

2. **Партиционирование (опционально для больших объемов):**
   - Таблица `notification_log` может быть партиционирована по месяцам для улучшения производительности при большом количестве записей

### Безопасность данных

1. **Шифрование:**
   - Sensitive данные (даты циклов) могут быть зашифрованы на уровне приложения
   - Использование SSL/TLS для подключения к БД

2. **Резервное копирование:**
   - Ежедневное резервное копирование всех таблиц
   - Хранение бэкапов минимум 30 дней

3. **GDPR соответствие:**
   - Возможность полного удаления данных пользователя
   - Возможность экспорта всех данных пользователя

## Миграции

### Начальная миграция

```sql
-- Создание таблицы users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_active_at TIMESTAMP,
    commands_count INTEGER DEFAULT 0,
    preferred_language VARCHAR(10) DEFAULT 'ru'
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Создание таблицы cycles
CREATE TABLE cycles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    cycle_length INTEGER NOT NULL CHECK (cycle_length BETWEEN 21 AND 40),
    period_length INTEGER NOT NULL CHECK (period_length BETWEEN 1 AND 10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_cycles_user_id ON cycles(user_id);
CREATE INDEX idx_cycles_is_current ON cycles(is_current);
CREATE INDEX idx_cycles_start_date ON cycles(start_date);
CREATE UNIQUE INDEX idx_cycles_user_current ON cycles(user_id, is_current) WHERE is_current = TRUE;

-- Создание таблицы notification_settings
CREATE TABLE notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    time_offset INTEGER DEFAULT 0,
    custom_time TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, notification_type)
);

CREATE INDEX idx_notification_settings_is_enabled ON notification_settings(is_enabled);

-- Создание таблицы notification_log
CREATE TABLE notification_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    sent_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_notification_log_user_id ON notification_log(user_id);
CREATE INDEX idx_notification_log_status ON notification_log(status);
CREATE INDEX idx_notification_log_sent_at ON notification_log(sent_at);
CREATE INDEX idx_notification_log_user_type_date ON notification_log(user_id, notification_type, sent_at);
```

## Примеры запросов

### 1. Получить активный цикл пользователя
```sql
SELECT * FROM cycles
WHERE user_id = ? AND is_current = TRUE
LIMIT 1;
```

### 2. Получить все активные уведомления пользователя
```sql
SELECT * FROM notification_settings
WHERE user_id = ? AND is_enabled = TRUE;
```

### 3. Получить историю циклов пользователя
```sql
SELECT * FROM cycles
WHERE user_id = ?
ORDER BY start_date DESC
LIMIT 10;
```

### 4. Статистика отправленных уведомлений
```sql
SELECT
    notification_type,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as sent,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed
FROM notification_log
WHERE user_id = ? AND sent_at >= NOW() - INTERVAL '30 days'
GROUP BY notification_type;
```

### 5. Активные пользователи за последние 7 дней
```sql
SELECT COUNT(DISTINCT user_id) as active_users
FROM notification_log
WHERE sent_at >= NOW() - INTERVAL '7 days' AND status = 'SENT';
```

## Требования к производительности

- Все основные запросы должны выполняться менее чем за 100ms
- База должна поддерживать минимум 10,000 активных пользователей
- Время отклика для операций записи не должно превышать 200ms
- База должна выдерживать до 100 запросов в секунду

## Масштабирование

При росте нагрузки рекомендуется:

1. **Вертикальное масштабирование:**
   - Увеличение ресурсов сервера БД
   - Оптимизация параметров PostgreSQL

2. **Горизонтальное масштабирование:**
   - Настройка репликации (master-slave)
   - Чтение из реплик, запись в master

3. **Кэширование:**
   - Использование Redis для кэширования частых запросов
   - Кэширование настроек пользователей

4. **Архивирование:**
   - Перенос старых записей из `notification_log` в архивные таблицы
   - Удаление логов старше 1 года