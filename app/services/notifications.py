"""Outbound notifications triggered from the web service.

The web process doesn't run the bot, but it can send Telegram messages
directly via the Bot API (httpx), so assignment notices go out immediately.
"""

from app.config import settings
from app.models import Meeting, Task, User
from app.services.telegram import send_message
from app.timeutil import LOCAL_TZ


async def notify_task_assigned(
    assignee: User | None, task: Task, account_name: str | None
) -> None:
    """DM the assignee that a task was assigned to them."""
    if not assignee or not assignee.telegram_chat_id:
        return
    lines = [
        "📌 На вас назначена задача",
        f"<b>{task.title}</b>",
    ]
    if account_name:
        lines.append(f"Клиент: {account_name}")
    if task.due_date:
        lines.append(
            f"Срок: {task.due_date.astimezone(LOCAL_TZ).strftime('%d.%m.%Y %H:%M')}"
        )
    lines.append(f"{settings.base_url}/accounts/{task.account_id}#tasks")
    await send_message(assignee.telegram_chat_id, "\n".join(lines))


async def notify_meeting_assigned(
    owner: User | None, meeting: Meeting, account_name: str | None
) -> None:
    """DM the responsible employee that a meeting was assigned to them."""
    if not owner or not owner.telegram_chat_id:
        return
    when = meeting.starts_at.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M")
    lines = [
        "🗓 Вам назначена встреча",
        f"<b>{meeting.title}</b>",
    ]
    if account_name:
        lines.append(f"Клиент: {account_name}")
    lines.append(f"Когда: {when}")
    if meeting.location:
        lines.append(f"Где: {meeting.location}")
    lines.append(f"{settings.base_url}/accounts/{meeting.account_id}#meetings")
    await send_message(owner.telegram_chat_id, "\n".join(lines))
