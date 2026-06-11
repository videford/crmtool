# crmTool

CRM для B2B-продаж (клиенты — банки и компании). Три части на одной БД:

- **Сайт** (FastAPI + HTMX + Tailwind) — карточки клиентов, сделки/воронка, встречи, задачи, команда с ролями.
- **Telegram-бот** (aiogram) — напоминания о встречах + быстрые команды `/today`, `/agenda`.
- **Linear** — задачи создаются автоматически (по этапам сделки) и вручную из карточки; статусы синхронизируются обратно через webhook.

## Стек
FastAPI · async SQLAlchemy 2.0 · PostgreSQL · aiogram 3 · APScheduler · httpx · Jinja2/HTMX. Деплой — Railway.

## Архитектура процессов
| Сервис | Команда | Назначение |
|---|---|---|
| `web` | `uvicorn app.main:app` | сайт + Linear webhook |
| `worker` | `python -m worker.main` | напоминания (APScheduler) + Telegram-бот (polling) |
| `db` | PostgreSQL | данные |

## Локальный запуск (Docker)
```bash
cp .env.example .env        # при необходимости впишите токены
docker compose up --build
```
Откройте http://localhost:8000 — вход по `ADMIN_EMAIL` / `ADMIN_PASSWORD` из `.env`
(по умолчанию `admin@example.com` / `admin123`).

При первом старте `app.init_db` создаёт таблицы и сидит admin-пользователя.

## Роли
- **admin** — всё, включая управление пользователями и удаление клиентов.
- **manager** — создание/редактирование клиентов, сделок, встреч, задач.
- **viewer** — только просмотр.

## Telegram
1. Создайте бота у @BotFather, вставьте токен в `TELEGRAM_BOT_TOKEN`.
2. В CRM → «Настройки» получите код привязки и отправьте боту `/start <код>`.
3. Напоминания шлются за `REMINDER_OFFSETS` минут до встречи (по умолчанию 1440, 60, 15).

## Linear
1. `LINEAR_API_KEY` (Personal API key) и `LINEAR_TEAM_ID`.
2. (Опц.) Webhook в Linear на `{BASE_URL}/linear/webhook`, ресурс Issues, секрет = `LINEAR_WEBHOOK_SECRET`.
   Задачи без настроенного Linear всё равно создаются локально.

## Деплой на Railway
1. Подключите репозиторий, добавьте плагин **PostgreSQL** (даёт `DATABASE_URL`).
2. Сервис **web** — деплоится по `railway.toml` (healthcheck `/health`).
3. Создайте второй сервис из того же репозитория, переопределив start command на
   `python -m worker.main`.
4. Задайте переменные окружения (см. `.env.example`): `SESSION_SECRET`, `BASE_URL`,
   `TELEGRAM_BOT_TOKEN`, `LINEAR_*`, `TIMEZONE`.

## Структура
```
app/        FastAPI: config, db, models, security, routers, services, bot, templating
worker/     APScheduler reminders + bot polling entrypoint
templates/  Jinja2 + HTMX (Tailwind via CDN)
alembic/    миграции (на старте используется create_all; см. app/init_db.py)
```
