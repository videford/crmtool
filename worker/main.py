"""Worker entrypoint.

Runs two things in one asyncio loop:
  1. APScheduler job firing meeting reminders every minute.
  2. The aiogram bot in polling mode (so /start linking and /today work).

Both degrade gracefully when TELEGRAM_BOT_TOKEN is unset: the scheduler keeps
running (and simply sends nothing), and the bot is skipped.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from worker.reminders import run_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")


async def _tick():
    try:
        sent = await run_once()
        if sent:
            log.info("Sent %d reminder(s)", sent)
    except Exception:  # noqa: BLE001
        log.exception("reminder tick failed")


async def main():
    # Make sure additive columns exist even if the worker boots before web.
    try:
        from app.init_db import ensure_columns

        await ensure_columns()
    except Exception:  # noqa: BLE001
        log.exception("ensure_columns failed (will rely on web migration)")

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(_tick, "interval", minutes=1, next_run_time=None)
    scheduler.start()
    log.info("Scheduler started (reminders every 1 min).")

    if settings.telegram_enabled:
        from app.bot.dispatcher import build_bot, dp, setup_bot_commands

        bot = build_bot()
        await setup_bot_commands(bot)
        log.info("Starting Telegram bot (polling)…")
        await dp.start_polling(bot, handle_signals=False)
    else:
        log.warning("TELEGRAM_BOT_TOKEN not set — bot disabled, scheduler only.")
        # Keep the process alive for the scheduler.
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
