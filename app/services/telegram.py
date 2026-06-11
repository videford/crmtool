"""Low-level Telegram sending via the Bot API (httpx).

Kept independent of the aiogram polling bot so the reminder worker can send
messages without owning a Dispatcher.
"""

import httpx

from app.config import settings

API_BASE = "https://api.telegram.org"


async def send_message(
    chat_id: str | int, text: str, parse_mode: str = "HTML"
) -> bool:
    if not settings.telegram_enabled:
        return False
    url = f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
    return resp.status_code == 200
