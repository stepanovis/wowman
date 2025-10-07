# Документация по разработке Telegram-бота для отслеживания женского цикла

## Оглавление

1. [Обзор проекта](#1-обзор-проекта)
2. [Функциональные требования](#2-функциональные-требования)
3. [Технический стек](#3-технический-стек)
4. [Архитектура приложения](#4-архитектура-приложения)
5. [Структура базы данных](#5-структура-базы-данных)
6. [Команды и сценарии взаимодействия](#6-команды-и-сценарии-взаимодействия)
7. [Логика расчета периодов цикла](#7-логика-расчета-периодов-цикла)
8. [Система уведомлений](#8-система-уведомлений)
9. [Конфигурация приложения](#9-конфигурация-приложения)
10. [Структура проекта](#10-структура-проекта)
11. [Требования к развертыванию](#11-требования-к-развертыванию)
12. [Безопасность и приватность](#12-безопасность-и-приватность)

---

## 1. Обзор проекта

### 1.1 Назначение

Telegram-бот для отслеживания женского цикла, предназначенный для пар, которые хотят заботиться друг о друге и поддерживать гармонию в отношениях. Бот отправляет ненавязчивые напоминания о важных периодах цикла партнерши.

### 1.2 Целевая аудитория

Пары, которые:
- Ведут совместную заботу о здоровье
- Планируют беременность или предохраняются
- Хотят быть внимательными к физиологическим особенностям партнерши

### 1.3 Ключевые принципы

- Заботливый и деликатный тон общения
- Ненавязчивые напоминания
- Простота использования
- Конфиденциальность данных

---

## 2. Функциональные требования

### 2.1 Первичная настройка

При первом запуске бот должен собрать следующие данные:

1. **Дата последних месячных** (обязательный параметр)
   - Формат: DD.MM.YYYY
   - Валидация: не позднее текущей даты, не ранее 90 дней назад

2. **Длительность цикла** (дней)
   - Значение по умолчанию: 28 дней
   - Диапазон: 21-35 дней
   - Возможность изменения

3. **Длительность месячных** (дней)
   - Значение по умолчанию: 5 дней
   - Диапазон: 3-7 дней
   - Возможность изменения

### 2.2 Типы напоминаний

Бот отправляет 5 типов уведомлений:

1. **Начало овуляции** (за 1 день до расчетной овуляции)
   - Сообщение: "Можно начинать делать ребеночка 👶"
   - Дополнительный контекст о благоприятном периоде

2. **Зона безопасного секса** (после завершения овуляционного окна)
   - Сообщение: "В этом месяце началась зона более безопасного секса 💚"
   - Указание на снижение вероятности зачатия

3. **Предупреждение за 3 дня**
   - Сообщение: "Через пару дней начнутся месячные, позаботься о своей любимой 💝"
   - Напоминание о заботе и подготовке

4. **Предупреждение за 1 день**
   - Сообщение: "Завтра месячные 📅"
   - Финальное напоминание

5. **Подтверждение начала** (в ожидаемый день начала)
   - Сообщение: "Сегодня начались месячные?"
   - Варианты ответа: "Да", "Вчера", "Выбрать дату"

### 2.3 Корректировка данных

После подтверждения фактической даты начала месячных:
- Пересчет следующего цикла
- Сохранение исторических данных для повышения точности
- Возможность скорректировать параметры цикла через настройки

---

## 3. Технический стек

### 3.1 Основные технологии

- **Язык программирования**: Python 3.11+
- **Telegram Bot Framework**: python-telegram-bot 20.x
- **База данных**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.x
- **Планировщик задач**: APScheduler
- **Контейнеризация**: Docker + Docker Compose
- **Управление конфигурацией**: python-dotenv

### 3.2 Дополнительные библиотеки

- `psycopg2-binary` - драйвер PostgreSQL
- `pytz` - работа с часовыми поясами
- `pydantic` - валидация данных
- `alembic` - миграции БД

---

## 4. Архитектура приложения

### 4.1 Общая архитектура

```
┌─────────────────┐
│   Telegram API  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│     Bot Handler Layer       │
│  (обработка команд и        │
│   callback'ов)              │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Business Logic Layer      │
│  - Расчет периодов          │
│  - Валидация данных         │
│  - Формирование сообщений   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Data Access Layer (ORM)   │
│  - CRUD операции            │
│  - Модели данных            │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   PostgreSQL Database       │
└─────────────────────────────┘

         ║ (параллельный процесс)
         ▼
┌─────────────────────────────┐
│  Notification Scheduler     │
│  (APScheduler)              │
│  - Проверка предстоящих     │
│    событий                  │
│  - Отправка напоминаний     │
└─────────────────────────────┘
```

### 4.2 Модульная структура

#### 4.2.1 Bot Module (`bot/`)
- `handlers.py` - обработчики команд и сообщений
- `keyboards.py` - inline и reply клавиатуры
- `messages.py` - текстовые шаблоны сообщений
- `states.py` - состояния для ConversationHandler

#### 4.2.2 Core Module (`core/`)
- `calculator.py` - расчет периодов цикла
- `validator.py` - валидация пользовательских данных
- `notifier.py` - логика отправки уведомлений
- `scheduler.py` - планирование задач

#### 4.2.3 Database Module (`database/`)
- `models.py` - SQLAlchemy модели
- `crud.py` - CRUD операции
- `connection.py` - подключение к БД

#### 4.2.4 Config Module (`config/`)
- `settings.py` - загрузка конфигурации
- `constants.py` - константы приложения

---

## 5. Структура базы данных

### 5.1 Таблица `users`

Хранит основные данные пользователей.

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(50) DEFAULT 'UTC'
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_is_active ON users(is_active);
```

### 5.2 Таблица `cycle_settings`

Хранит настройки цикла пользователя.

```sql
CREATE TABLE cycle_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    cycle_length INTEGER NOT NULL DEFAULT 28,
    period_length INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT cycle_length_check CHECK (cycle_length BETWEEN 21 AND 35),
    CONSTRAINT period_length_check CHECK (period_length BETWEEN 3 AND 7),
    CONSTRAINT user_id_unique UNIQUE (user_id)
);

CREATE INDEX idx_cycle_settings_user_id ON cycle_settings(user_id);
```

### 5.3 Таблица `cycle_records`

Хранит историю фактических циклов для повышения точности прогнозов.

```sql
CREATE TABLE cycle_records (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE,
    is_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cycle_records_user_id ON cycle_records(user_id);
CREATE INDEX idx_cycle_records_start_date ON cycle_records(start_date);
CREATE INDEX idx_cycle_records_is_confirmed ON cycle_records(is_confirmed);
```

### 5.4 Таблица `notifications`

Логирование отправленных уведомлений (для избежания дублей).

```sql
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    scheduled_date DATE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_notification UNIQUE (user_id, notification_type, scheduled_date)
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_scheduled_date ON notifications(scheduled_date);
```

### 5.5 Перечисление типов уведомлений

```python
# В коде приложения
class NotificationType(str, Enum):
    OVULATION_START = "ovulation_start"
    SAFE_ZONE_START = "safe_zone_start"
    PERIOD_IN_3_DAYS = "period_in_3_days"
    PERIOD_TOMORROW = "period_tomorrow"
    PERIOD_CONFIRMATION = "period_confirmation"
```

---

## 6. Команды и сценарии взаимодействия

### 6.1 Основные команды

#### 6.1.1 `/start`

**Назначение**: Первый запуск бота, приветствие и начало настройки.

**Сценарий**:
1. Проверка наличия пользователя в БД
2. Если новый пользователь:
   - Отображение приветственного сообщения
   - Начало процесса первичной настройки
3. Если существующий пользователь:
   - Приветствие с именем
   - Отображение основного меню

**Приветственное сообщение**:
```
Привет! 👋

Я бот-помощник для заботы о вашей паре.

Моя цель — помочь вам быть внимательными друг к другу, напоминая о важных моментах женского цикла. Это поможет вам:

💚 Лучше понимать физическое состояние вашей партнерши
💝 Проявлять заботу в нужные моменты
👶 Планировать зачатие или предохраняться осознанно
🤝 Укреплять доверие и близость в отношениях

Я буду отправлять ненавязчивые напоминания о:
• Периоде овуляции (для планирования беременности)
• Безопасных днях цикла
• Приближении месячных

Все данные строго конфиденциальны и защищены.

Давайте начнем настройку! 🌸
```

#### 6.1.2 `/setup`

**Назначение**: Запуск процесса настройки/перенастройки параметров цикла.

**Сценарий**:
1. Запрос даты последних месячных
2. Запрос длительности цикла (с предложением значения по умолчанию)
3. Запрос длительности месячных (с предложением значения по умолчанию)
4. Подтверждение и сохранение данных
5. Расчет и отображение ближайших важных дат

**Пошаговые сообщения**:

**Шаг 1**: Запрос даты последних месячных
```
Когда начались последние месячные? 📅

Пожалуйста, введите дату в формате ДД.ММ.ГГГГ
Например: 15.09.2025
```

**Шаг 2**: Запрос длительности цикла
```
Какова обычная длительность цикла? 🔄

Стандартная длительность — 28 дней.
Вы можете оставить это значение или ввести свое (от 21 до 35 дней).

[Кнопка: Оставить 28 дней] [Ввести свое значение]
```

**Шаг 3**: Запрос длительности месячных
```
Какова обычная длительность месячных? 🌸

Стандартная длительность — 5 дней.
Вы можете оставить это значение или ввести свое (от 3 до 7 дней).

[Кнопка: Оставить 5 дней] [Ввести свое значение]
```

**Шаг 4**: Подтверждение данных
```
Отлично! Давайте проверим введенные данные:

📅 Дата последних месячных: 15.09.2025
🔄 Длительность цикла: 28 дней
🌸 Длительность месячных: 5 дней

Все верно?

[Да, сохранить] [Изменить]
```

**Шаг 5**: Успешное сохранение
```
Настройка завершена! ✅

На основе ваших данных:

👶 Овуляция ожидается: ~26.09.2025
💚 Безопасный период начнется: ~29.09.2025
📅 Следующие месячные: ~13.10.2025

Я буду отправлять напоминания в ключевые моменты.
Желаю вам гармонии и заботы! 💝
```

#### 6.1.3 `/calendar`

**Назначение**: Отображение календаря текущего и следующего циклов.

**Формат ответа**:
```
Календарь вашего цикла 📅

ТЕКУЩИЙ ЦИКЛ:
Начало: 15.09.2025
Завершение месячных: ~19.09.2025
Овуляция: ~26.09.2025 (24-28.09)
Безопасный период: с 29.09.2025

СЛЕДУЮЩИЙ ЦИКЛ:
Ожидаемое начало: 13.10.2025

[Обновить данные]
```

#### 6.1.4 `/settings`

**Назначение**: Управление настройками бота.

**Опции**:
- Изменить параметры цикла
- Отключить/включить уведомления
- Удалить все данные

**Интерфейс**:
```
Настройки ⚙️

Ваши текущие параметры:
🔄 Длительность цикла: 28 дней
🌸 Длительность месячных: 5 дней
🔔 Уведомления: включены

[Изменить параметры цикла]
[Отключить уведомления]
[Удалить все мои данные]
[Назад в меню]
```

#### 6.1.5 `/help`

**Назначение**: Справка по использованию бота.

**Содержание**:
```
Помощь 📖

КАК ПОЛЬЗОВАТЬСЯ БОТОМ:

/start — Начать работу или вернуться в главное меню
/setup — Настроить параметры цикла
/calendar — Посмотреть календарь циклов
/settings — Управление настройками
/help — Показать эту справку

ЧТО ДЕЛАЕТ БОТ:

💡 Отслеживает женский цикл на основе ваших данных
📬 Отправляет напоминания о важных периодах
🔒 Обеспечивает конфиденциальность ваших данных

ТИПЫ УВЕДОМЛЕНИЙ:

👶 Период овуляции (для планирования)
💚 Начало безопасного периода
💝 Предупреждение за 3 дня до месячных
📅 Напоминание за 1 день
✅ Подтверждение фактического начала

Если у вас есть вопросы, напишите @support_username
```

### 6.2 Сценарий подтверждения начала месячных

**Триггер**: В расчетный день начала месячных (в 09:00 по часовому поясу пользователя).

**Сообщение**:
```
Доброе утро! ☀️

Сегодня ожидается начало месячных.
Они уже начались? 🌸

[Да, сегодня] [Вчера] [Выбрать другую дату] [Еще нет]
```

**Обработка ответов**:

1. **"Да, сегодня"**:
   - Создание новой записи цикла с текущей датой
   - Пересчет следующего цикла
   - Подтверждение: "Спасибо! Данные обновлены. Следующий цикл ожидается 10.11.2025."

2. **"Вчера"**:
   - Создание записи с датой вчера
   - Пересчет следующего цикла
   - Подтверждение: "Спасибо! Данные обновлены."

3. **"Выбрать другую дату"**:
   - Запрос даты в формате ДД.ММ.ГГГГ
   - Валидация (не более 5 дней назад/вперед)
   - Сохранение и пересчет

4. **"Еще нет"**:
   - Отложенное напоминание через 24 часа
   - "Хорошо, я напомню завтра!"

### 6.3 Сценарий корректировки цикла

Если фактическая дата начала отличается от расчетной более чем на 2 дня, бот предлагает скорректировать параметры:

```
Заметил, что месячные начались на 3 дня раньше, чем ожидалось.

Хотите, чтобы я скорректировал длительность цикла для более точных прогнозов?

Текущая длительность: 28 дней
Фактическая в этом месяце: 25 дней

[Да, скорректировать] [Оставить как есть]
```

---

## 7. Логика расчета периодов цикла

### 7.1 Основные периоды

#### 7.1.1 Менструация
- **Начало**: дата последних месячных
- **Продолжительность**: значение из `period_length`
- **Конец**: `start_date + period_length - 1`

#### 7.1.2 Фолликулярная фаза
- **Начало**: после окончания менструации
- **Продолжительность**: до овуляции

#### 7.1.3 Овуляция
- **Расчетный день**: `start_date + cycle_length - 14`
- **Окно фертильности**: 5 дней (2 дня до овуляции + день овуляции + 2 дня после)
- **Формула окна**: `[ovulation_day - 2, ovulation_day + 2]`

#### 7.1.4 Лютеиновая фаза (безопасный период)
- **Начало**: `ovulation_day + 3`
- **Продолжительность**: до начала следующего цикла

#### 7.1.5 Следующий цикл
- **Расчетная дата**: `start_date + cycle_length`

### 7.2 Алгоритм расчета

```python
from datetime import datetime, timedelta
from typing import Tuple

def calculate_cycle_periods(
    last_period_date: datetime,
    cycle_length: int,
    period_length: int
) -> dict:
    """
    Рассчитывает все ключевые периоды цикла.

    Args:
        last_period_date: Дата начала последних месячных
        cycle_length: Длительность цикла (дней)
        period_length: Длительность месячных (дней)

    Returns:
        Словарь с ключевыми датами и периодами
    """

    # Окончание менструации
    period_end_date = last_period_date + timedelta(days=period_length - 1)

    # День овуляции (за 14 дней до следующих месячных)
    ovulation_day = last_period_date + timedelta(days=cycle_length - 14)

    # Окно фертильности (5 дней)
    fertile_window_start = ovulation_day - timedelta(days=2)
    fertile_window_end = ovulation_day + timedelta(days=2)

    # Начало безопасного периода
    safe_period_start = fertile_window_end + timedelta(days=1)

    # Дата следующего цикла
    next_period_date = last_period_date + timedelta(days=cycle_length)

    # Даты для уведомлений
    notification_3_days_before = next_period_date - timedelta(days=3)
    notification_1_day_before = next_period_date - timedelta(days=1)
    notification_ovulation = ovulation_day - timedelta(days=1)

    return {
        "period_start": last_period_date,
        "period_end": period_end_date,
        "ovulation_day": ovulation_day,
        "fertile_window_start": fertile_window_start,
        "fertile_window_end": fertile_window_end,
        "safe_period_start": safe_period_start,
        "next_period_date": next_period_date,
        "notifications": {
            "ovulation_alert": notification_ovulation,
            "safe_zone_alert": safe_period_start,
            "period_3_days": notification_3_days_before,
            "period_1_day": notification_1_day_before,
            "period_confirmation": next_period_date
        }
    }
```

### 7.3 Корректировка на основе истории

Для повышения точности прогнозов используется средняя длительность цикла на основе последних 3-6 записей:

```python
def calculate_average_cycle_length(user_id: int, records_count: int = 3) -> int:
    """
    Вычисляет среднюю длительность цикла на основе истории.

    Args:
        user_id: ID пользователя
        records_count: Количество последних циклов для анализа

    Returns:
        Средняя длительность цикла (дней)
    """
    # Получить последние N подтвержденных записей
    records = get_confirmed_cycle_records(user_id, limit=records_count)

    if len(records) < 2:
        # Недостаточно данных для расчета
        return get_user_default_cycle_length(user_id)

    cycle_lengths = []
    for i in range(len(records) - 1):
        current = records[i].start_date
        previous = records[i + 1].start_date
        length = (current - previous).days
        cycle_lengths.append(length)

    # Средняя длительность с округлением
    average_length = round(sum(cycle_lengths) / len(cycle_lengths))

    # Ограничение в пределах нормы (21-35 дней)
    return max(21, min(35, average_length))
```

---

## 8. Система уведомлений

### 8.1 Типы уведомлений и их тексты

#### 8.1.1 Уведомление об овуляции (за 1 день)

**Время отправки**: 20:00

```
Привет! 👋

Завтра начинается период овуляции — самое благоприятное время для зачатия. 👶

Если вы планируете ребеночка, следующие 3-4 дня будут особенно важными.

Заботьтесь друг о друге! 💝
```

#### 8.1.2 Начало безопасного периода

**Время отправки**: 09:00

```
Доброе утро! ☀️

В этом месяце началась зона более безопасного секса. 💚

Вероятность зачатия сейчас значительно снижена, но помните, что ни один естественный метод не дает 100% гарантии.

Будьте счастливы! 😊
```

#### 8.1.3 Предупреждение за 3 дня

**Время отправки**: 18:00

```
Привет! 👋

Через пару дней начнутся месячные. 🌸

Сейчас самое время позаботиться о своей любимой:
• Запастись необходимыми средствами гигиены
• Быть особенно внимательным и нежным
• Приготовить что-нибудь вкусное или удивить приятным сюрпризом

Забота в такие моменты особенно ценна! 💝
```

#### 8.1.4 Предупреждение за 1 день

**Время отправки**: 20:00

```
Напоминаю: завтра месячные. 📅

Будьте рядом и заботьтесь друг о друге! 💚
```

#### 8.1.5 Подтверждение начала (см. раздел 6.2)

**Время отправки**: 09:00

### 8.2 Механизм работы планировщика

#### 8.2.1 Структура планировщика

Используется APScheduler с PostgreSQL в качестве хранилища задач для обеспечения персистентности.

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pytz import utc

# Конфигурация планировщика
jobstores = {
    'default': SQLAlchemyJobStore(url='postgresql://...')
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=utc)
```

#### 8.2.2 Создание задач уведомлений

При сохранении/обновлении данных цикла:

```python
def schedule_notifications_for_user(user_id: int):
    """
    Создает все запланированные уведомления для пользователя.
    """
    # Получить данные пользователя и рассчитать периоды
    user_data = get_user_cycle_data(user_id)
    periods = calculate_cycle_periods(
        user_data.last_period_date,
        user_data.cycle_length,
        user_data.period_length
    )

    # Получить часовой пояс пользователя
    tz = get_user_timezone(user_id)

    # Удалить старые задачи для пользователя
    remove_user_jobs(user_id)

    # Создать задачи для каждого типа уведомления
    notifications = periods["notifications"]

    # 1. Уведомление об овуляции (20:00)
    scheduler.add_job(
        send_ovulation_notification,
        'date',
        run_date=notifications["ovulation_alert"].replace(hour=20, tzinfo=tz),
        args=[user_id],
        id=f'ovulation_{user_id}',
        replace_existing=True
    )

    # 2. Начало безопасного периода (09:00)
    scheduler.add_job(
        send_safe_zone_notification,
        'date',
        run_date=notifications["safe_zone_alert"].replace(hour=9, tzinfo=tz),
        args=[user_id],
        id=f'safe_zone_{user_id}',
        replace_existing=True
    )

    # 3. Предупреждение за 3 дня (18:00)
    scheduler.add_job(
        send_period_in_3_days_notification,
        'date',
        run_date=notifications["period_3_days"].replace(hour=18, tzinfo=tz),
        args=[user_id],
        id=f'period_3days_{user_id}',
        replace_existing=True
    )

    # 4. Предупреждение за 1 день (20:00)
    scheduler.add_job(
        send_period_tomorrow_notification,
        'date',
        run_date=notifications["period_1_day"].replace(hour=20, tzinfo=tz),
        args=[user_id],
        id=f'period_1day_{user_id}',
        replace_existing=True
    )

    # 5. Подтверждение начала (09:00)
    scheduler.add_job(
        send_period_confirmation_request,
        'date',
        run_date=notifications["period_confirmation"].replace(hour=9, tzinfo=tz),
        args=[user_id],
        id=f'period_confirm_{user_id}',
        replace_existing=True
    )
```

#### 8.2.3 Предотвращение дублирования

Перед отправкой уведомления проверяется таблица `notifications`:

```python
async def send_notification_if_not_sent(
    user_id: int,
    notification_type: str,
    scheduled_date: datetime
):
    """
    Отправляет уведомление только если оно еще не было отправлено.
    """
    # Проверка в БД
    already_sent = check_notification_sent(
        user_id,
        notification_type,
        scheduled_date.date()
    )

    if already_sent:
        return

    # Отправка уведомления
    await send_notification(user_id, notification_type)

    # Логирование в БД
    log_notification(user_id, notification_type, scheduled_date.date())
```

---

## 9. Конфигурация приложения

### 9.1 Файл `.env`

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
BOT_ID=your_bot_id_here

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=ovulo_db
DB_USER=ovulo_user
DB_PASSWORD=your_secure_password_here

# Application Settings
TIMEZONE=Europe/Moscow
LOG_LEVEL=INFO
ENVIRONMENT=production

# Notification Settings
DEFAULT_CYCLE_LENGTH=28
DEFAULT_PERIOD_LENGTH=5
MIN_CYCLE_LENGTH=21
MAX_CYCLE_LENGTH=35
MIN_PERIOD_LENGTH=3
MAX_PERIOD_LENGTH=7

# Feature Flags
ENABLE_NOTIFICATIONS=true
ENABLE_AUTO_CORRECTION=true
```

### 9.2 Структура `config/settings.py`

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Bot settings
    bot_token: str
    bot_id: str

    # Database settings
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # Application settings
    timezone: str = "UTC"
    log_level: str = "INFO"
    environment: str = "production"

    # Cycle defaults
    default_cycle_length: int = 28
    default_period_length: int = 5
    min_cycle_length: int = 21
    max_cycle_length: int = 35
    min_period_length: int = 3
    max_period_length: int = 7

    # Feature flags
    enable_notifications: bool = True
    enable_auto_correction: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## 10. Структура проекта

```
ovulo/
│
├── bot/
│   ├── __init__.py
│   ├── handlers.py           # Обработчики команд и сообщений
│   ├── keyboards.py          # Клавиатуры (inline и reply)
│   ├── messages.py           # Текстовые шаблоны
│   └── states.py             # Состояния ConversationHandler
│
├── core/
│   ├── __init__.py
│   ├── calculator.py         # Расчет периодов цикла
│   ├── validator.py          # Валидация данных
│   ├── notifier.py           # Отправка уведомлений
│   └── scheduler.py          # Планирование задач
│
├── database/
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy модели
│   ├── crud.py               # CRUD операции
│   ├── connection.py         # Подключение к БД
│   └── migrations/           # Alembic миграции
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│
├── config/
│   ├── __init__.py
│   ├── settings.py           # Конфигурация приложения
│   └── constants.py          # Константы
│
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py
│   ├── test_validator.py
│   ├── test_handlers.py
│   └── test_crud.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/
│   ├── init_db.py            # Инициализация БД
│   └── create_migration.py   # Создание миграций
│
├── .env.example
├── .gitignore
├── requirements.txt
├── alembic.ini
├── main.py                   # Точка входа
└── README.md
```

---

## 11. Требования к развертыванию

### 11.1 Docker Compose конфигурация

**Файл `docker/docker-compose.yml`**:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: ovulo_postgres
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: ovulo_bot
    env_file:
      - ../.env
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ../logs:/app/logs
    command: python main.py

volumes:
  postgres_data:
```

### 11.2 Dockerfile

**Файл `docker/Dockerfile`**:

```dockerfile
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Запуск приложения
CMD ["python", "main.py"]
```

### 11.3 Requirements.txt

```txt
python-telegram-bot==20.7
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pydantic==2.5.2
pydantic-settings==2.1.0
python-dotenv==1.0.0
APScheduler==3.10.4
pytz==2023.3
```

### 11.4 Инструкция по развертыванию

#### 11.4.1 Подготовка сервера

1. Установить Docker и Docker Compose:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

2. Клонировать репозиторий:
```bash
git clone <repository_url>
cd ovulo
```

3. Создать файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
nano .env  # Отредактировать конфигурацию
```

#### 11.4.2 Запуск приложения

1. Собрать и запустить контейнеры:
```bash
docker-compose -f docker/docker-compose.yml up -d
```

2. Применить миграции БД:
```bash
docker exec -it ovulo_bot alembic upgrade head
```

3. Проверить статус:
```bash
docker-compose -f docker/docker-compose.yml ps
docker logs ovulo_bot
```

#### 11.4.3 Обновление приложения

```bash
git pull origin main
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml build --no-cache
docker-compose -f docker/docker-compose.yml up -d
docker exec -it ovulo_bot alembic upgrade head
```

#### 11.4.4 Резервное копирование БД

```bash
# Создание бэкапа
docker exec -t ovulo_postgres pg_dump -U ovulo_user ovulo_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
docker exec -i ovulo_postgres psql -U ovulo_user ovulo_db < backup_20250930_120000.sql
```

### 11.5 Мониторинг и логирование

#### 11.5.1 Структура логов

```python
import logging
from logging.handlers import RotatingFileHandler

# Конфигурация логгера
logger = logging.getLogger('ovulo')
logger.setLevel(logging.INFO)

# Файловый хендлер
file_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
)

# Консольный хендлер
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(levelname)s - %(message)s')
)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
```

#### 11.5.2 Ключевые метрики для мониторинга

- Количество активных пользователей
- Количество отправленных уведомлений (по типам)
- Ошибки при отправке сообщений
- Время отклика БД
- Использование памяти и CPU контейнеров

---

## 12. Безопасность и приватность

### 12.1 Принципы обработки данных

1. **Минимизация данных**: хранятся только необходимые параметры
2. **Шифрование**: использование SSL для подключения к БД
3. **Изоляция**: каждый пользователь видит только свои данные
4. **Удаление по запросу**: возможность полного удаления данных

### 12.2 GDPR-совместимые функции

#### 12.2.1 Удаление данных пользователя

```python
def delete_user_data(user_id: int):
    """
    Полное удаление всех данных пользователя из системы.
    """
    with db.session() as session:
        # Каскадное удаление связанных данных благодаря ON DELETE CASCADE
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            session.delete(user)
            session.commit()
```

#### 12.2.2 Экспорт данных

```python
def export_user_data(user_id: int) -> dict:
    """
    Экспорт всех данных пользователя в JSON формате.
    """
    user = get_user_by_telegram_id(user_id)
    cycle_settings = get_cycle_settings(user.id)
    cycle_records = get_all_cycle_records(user.id)

    return {
        "user_info": {
            "telegram_id": user.telegram_id,
            "created_at": user.created_at.isoformat(),
        },
        "cycle_settings": {
            "cycle_length": cycle_settings.cycle_length,
            "period_length": cycle_settings.period_length,
        },
        "cycle_history": [
            {
                "start_date": record.start_date.isoformat(),
                "is_confirmed": record.is_confirmed
            }
            for record in cycle_records
        ]
    }
```

### 12.3 Безопасность конфигурации

1. **Переменные окружения**: все секреты хранятся в `.env`
2. **Ограничение доступа**: PostgreSQL доступен только внутри Docker сети
3. **Регулярные обновления**: использование последних версий зависимостей
4. **Валидация входных данных**: проверка всех пользовательских данных

### 12.4 Обработка ошибок

```python
async def error_handler(update: Update, context: CallbackContext):
    """
    Глобальный обработчик ошибок.
    """
    logger.error(f"Update {update} caused error {context.error}")

    # Отправка дружелюбного сообщения пользователю
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

    # Уведомление администратора о критических ошибках
    if is_critical_error(context.error):
        await notify_admin(context.error)
```

---

## Заключение

Данная документация содержит все необходимые технические и функциональные спецификации для разработки Telegram-бота по отслеживанию женского цикла.

**Следующие шаги**:
1. Создание структуры проекта
2. Настройка БД и миграций
3. Реализация базовых моделей и CRUD операций
4. Разработка обработчиков команд
5. Внедрение логики расчета периодов
6. Настройка системы уведомлений
7. Тестирование всех сценариев
8. Подготовка к развертыванию

**Расчетное время разработки**: 40-50 часов чистого кодинга.

**Приоритет функций**:
1. Критические: регистрация, настройка, расчет периодов, базовые уведомления
2. Высокие: подтверждение начала месячных, корректировка цикла
3. Средние: календарь, детальные настройки
4. Низкие: экспорт данных, дополнительная аналитика

Документация готова к использованию для начала разработки. При необходимости разделы могут быть детализированы или дополнены в процессе разработки.

---