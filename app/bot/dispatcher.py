"""aiogram bot: account linking + quick meeting lookups.

Runs in polling mode inside the worker process (see worker/main.py), which
keeps deployment simple — no public webhook URL juggling required.
"""

from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import SessionLocal
from app.models import Meeting, User
from app.timeutil import LOCAL_TZ, now_utc

dp = Dispatcher()


@dp.message(CommandStart(deep_link=True))
@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    code = (command.args or "").strip()
    chat_id = str(message.chat.id)

    async with SessionLocal() as session:
        # Already linked?
        linked = await session.scalar(
            select(User).where(User.telegram_chat_id == chat_id)
        )
        if linked:
            await message.answer(
                f"Вы уже подключены как {linked.name}. "
                "Команды: /today — встречи на сегодня, /agenda — на неделю."
            )
            return

        if not code:
            await message.answer(
                "Привет! Чтобы подключить уведомления, откройте раздел "
                "«Настройки» в CRM, получите код и отправьте сюда:\n"
                "/start <код>"
            )
            return

        user = await session.scalar(
            select(User).where(User.telegram_link_code == code)
        )
        if user is None:
            await message.answer("Код не найден или устарел. Сгенерируйте новый в CRM.")
            return

        user.telegram_chat_id = chat_id
        user.telegram_link_code = None
        await session.commit()
        await message.answer(
            f"✅ Готово, {user.name}! Буду присылать напоминания о встречах.\n"
            "Команды: /today, /agenda."
        )


async def _meetings_for(chat_id: str, until_days: int) -> list[Meeting]:
    async with SessionLocal() as session:
        user = await session.scalar(
            select(User).where(User.telegram_chat_id == chat_id)
        )
        if user is None:
            return []
        now = now_utc()
        horizon = now + timedelta(days=until_days)
        stmt = (
            select(Meeting)
            .options(selectinload(Meeting.account))
            .where(
                Meeting.starts_at >= now - timedelta(hours=1),
                Meeting.starts_at <= horizon,
            )
            .order_by(Meeting.starts_at.asc())
        )
        # Owners see their meetings; everyone sees unassigned ones too.
        return [
            mt
            for mt in (await session.scalars(stmt)).all()
            if mt.owner_id in (None, user.id)
        ]


def _fmt(meetings: list[Meeting]) -> str:
    if not meetings:
        return "Встреч не найдено."
    lines = []
    for mt in meetings:
        when = mt.starts_at.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")
        loc = f" · {mt.location}" if mt.location else ""
        lines.append(f"🕒 {when} — <b>{mt.account.name}</b>: {mt.title}{loc}")
    return "\n".join(lines)


@dp.message(Command("today"))
async def cmd_today(message: Message):
    meetings = await _meetings_for(str(message.chat.id), until_days=1)
    today = [
        m
        for m in meetings
        if m.starts_at.astimezone(LOCAL_TZ).date()
        == now_utc().astimezone(LOCAL_TZ).date()
    ]
    await message.answer("<b>Встречи на сегодня</b>\n" + _fmt(today))


@dp.message(Command("agenda"))
async def cmd_agenda(message: Message):
    meetings = await _meetings_for(str(message.chat.id), until_days=7)
    await message.answer("<b>Встречи на 7 дней</b>\n" + _fmt(meetings))


def build_bot() -> Bot:
    from aiogram.client.default import DefaultBotProperties

    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
