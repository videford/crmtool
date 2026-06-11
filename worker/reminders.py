"""Meeting reminder logic, run on a 1-minute schedule by the worker.

Idempotency: each meeting tracks which reminder offsets have already been
sent (`reminded_offsets`), persisted in the DB, so reminders survive worker
restarts and never double-fire. If the worker was down across several
offsets, only the nearest one is sent and the missed larger offsets are
marked as handled.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import SessionLocal
from app.models import Meeting, User
from app.services.telegram import send_message
from app.timeutil import LOCAL_TZ, now_utc


def _reminder_text(meeting: Meeting, minutes_left: int) -> str:
    when = meeting.starts_at.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")
    if minutes_left >= 120:
        lead = f"через ~{minutes_left // 60} ч"
    elif minutes_left >= 1:
        lead = f"через ~{minutes_left} мин"
    else:
        lead = "сейчас"
    parts = [
        f"🔔 Встреча {lead}",
        f"🏢 <b>{meeting.account.name}</b> — {meeting.title}",
        f"🕒 {when}",
    ]
    if meeting.location:
        parts.append(f"🔗 {meeting.location}")
    if meeting.participants:
        parts.append(f"👥 {meeting.participants}")
    parts.append(f"{settings.base_url}/accounts/{meeting.account_id}#meetings")
    return "\n".join(parts)


async def _recipients(session, meeting: Meeting) -> list[User]:
    linked = (
        await session.scalars(
            select(User).where(User.telegram_chat_id.is_not(None))
        )
    ).all()
    if meeting.owner_id:
        owners = [u for u in linked if u.id == meeting.owner_id]
        if owners:
            return owners
    # No owner, or owner not linked → notify everyone linked.
    return linked


async def run_once() -> int:
    """Send any due reminders. Returns the number of messages sent."""
    if not settings.telegram_enabled:
        return 0

    offsets = settings.reminder_offset_minutes  # e.g. [1440, 60, 15]
    if not offsets:
        return 0

    now = now_utc()
    horizon = now + timedelta(minutes=max(offsets) + 1)
    sent = 0

    async with SessionLocal() as session:
        meetings = (
            await session.scalars(
                select(Meeting)
                .options(selectinload(Meeting.account))
                .where(Meeting.starts_at > now, Meeting.starts_at <= horizon)
            )
        ).all()

        for meeting in meetings:
            minutes_left = int((meeting.starts_at - now).total_seconds() // 60)
            already = set(meeting.reminded_offsets or [])
            due = [o for o in offsets if o >= minutes_left and o not in already]
            if not due:
                continue

            recipients = await _recipients(session, meeting)
            text = _reminder_text(meeting, minutes_left)
            for user in recipients:
                if await send_message(user.telegram_chat_id, text):
                    sent += 1

            # Mark all currently-due offsets as handled (incl. missed ones).
            meeting.reminded_offsets = sorted(already | set(due))

        await session.commit()

    return sent
