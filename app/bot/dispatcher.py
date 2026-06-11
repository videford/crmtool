"""aiogram bot: rich CRM control from Telegram.

Runs in polling mode inside the worker process (see worker/main.py).

Features:
  • Account linking via /start <code>
  • Persistent reply-keyboard menu (Clients / Meetings / Tasks / Pipeline)
  • Free-text client search → inline client cards
  • Client card: deals, next meeting, contacts, open tasks, quick actions
  • Open tasks with one-tap "done / in progress" buttons
  • Add a note or a task to a client right from chat (FSM)
  • Pipeline summary (count + sum per stage)
"""

from datetime import timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import SessionLocal
from app.models import Account, Deal, Meeting, Task, User
from app.services.activities import log_activity
from app.services.linear import create_task_with_linear
from app.timeutil import LOCAL_TZ, now_utc

dp = Dispatcher()

# Reply-keyboard menu labels
BTN_CLIENTS = "📇 Клиенты"
BTN_MEETINGS = "📅 Встречи"
BTN_TASKS = "✅ Задачи"
BTN_PIPELINE = "📊 Воронка"
MENU_BUTTONS = {BTN_CLIENTS, BTN_MEETINGS, BTN_TASKS, BTN_PIPELINE}


class Flow(StatesGroup):
    note = State()
    task = State()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text=BTN_CLIENTS)
    kb.button(text=BTN_MEETINGS)
    kb.button(text=BTN_TASKS)
    kb.button(text=BTN_PIPELINE)
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


async def _user(session, chat_id: str) -> User | None:
    return await session.scalar(
        select(User).where(User.telegram_chat_id == chat_id)
    )


async def require_user(message: Message, session) -> User | None:
    user = await _user(session, str(message.chat.id))
    if user is None:
        await message.answer(
            "Вы не подключены. Откройте «Настройки» в CRM, получите код и "
            "отправьте сюда: /start <код>"
        )
    return user


def _crm_url(path: str) -> str:
    return f"{settings.base_url}{path}"


# --------------------------------------------------------------------------- #
# Linking & menu
# --------------------------------------------------------------------------- #


@dp.message(CommandStart(deep_link=True))
@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    code = (command.args or "").strip()
    chat_id = str(message.chat.id)
    async with SessionLocal() as session:
        linked = await _user(session, chat_id)
        if linked:
            await message.answer(
                f"С возвращением, {linked.name}! Выберите раздел ниже.",
                reply_markup=main_menu(),
            )
            return
        if not code:
            await message.answer(
                "Привет! Чтобы подключить уведомления, откройте «Настройки» в "
                "CRM, получите код и отправьте сюда:\n/start <код>"
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
            "Пользуйтесь меню ниже или командой /help.",
            reply_markup=main_menu(),
        )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Команды</b>\n"
        "/today — встречи на сегодня\n"
        "/agenda — встречи на 7 дней\n"
        "/clients — список клиентов\n"
        "/tasks — открытые задачи\n"
        "/deals — сводка по воронке\n"
        "/menu — показать меню\n\n"
        "💡 Просто напишите название клиента — найду карточку.",
        reply_markup=main_menu(),
    )


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Меню:", reply_markup=main_menu())


# --------------------------------------------------------------------------- #
# Meetings
# --------------------------------------------------------------------------- #


async def _meetings_for(session, user: User, until_days: int) -> list[Meeting]:
    now = now_utc()
    stmt = (
        select(Meeting)
        .options(selectinload(Meeting.account))
        .where(
            Meeting.starts_at >= now - timedelta(hours=1),
            Meeting.starts_at <= now + timedelta(days=until_days),
        )
        .order_by(Meeting.starts_at.asc())
    )
    return [
        mt
        for mt in (await session.scalars(stmt)).all()
        if mt.owner_id in (None, user.id)
    ]


def _fmt_meetings(meetings: list[Meeting]) -> str:
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
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        meetings = await _meetings_for(session, user, until_days=1)
        today = now_utc().astimezone(LOCAL_TZ).date()
        meetings = [
            m for m in meetings if m.starts_at.astimezone(LOCAL_TZ).date() == today
        ]
        await message.answer("<b>Встречи на сегодня</b>\n" + _fmt_meetings(meetings))


@dp.message(Command("agenda"))
@dp.message(F.text == BTN_MEETINGS)
async def cmd_agenda(message: Message):
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        meetings = await _meetings_for(session, user, until_days=7)
        await message.answer("<b>Встречи на 7 дней</b>\n" + _fmt_meetings(meetings))


# --------------------------------------------------------------------------- #
# Clients: list, search, card
# --------------------------------------------------------------------------- #


def _clients_kb(accounts: list[Account]):
    kb = InlineKeyboardBuilder()
    for a in accounts:
        label = ("🏦 " if a.type == "bank" else "🏢 ") + a.name
        kb.button(text=label[:60], callback_data=f"acc:{a.id}")
    kb.adjust(1)
    return kb.as_markup()


@dp.message(Command("clients"))
@dp.message(F.text == BTN_CLIENTS)
async def cmd_clients(message: Message):
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        accounts = (
            await session.scalars(
                select(Account).order_by(Account.created_at.desc()).limit(10)
            )
        ).all()
        if not accounts:
            await message.answer("Клиентов пока нет.")
            return
        await message.answer(
            "<b>Последние клиенты</b>\nИли напишите название для поиска:",
            reply_markup=_clients_kb(accounts),
        )


@dp.callback_query(F.data.startswith("acc:"))
async def cb_account_card(cq: CallbackQuery):
    account_id = int(cq.data.split(":")[1])
    async with SessionLocal() as session:
        account = await session.get(
            Account,
            account_id,
            options=[
                selectinload(Account.owner),
                selectinload(Account.contacts),
                selectinload(Account.deals),
                selectinload(Account.tasks),
            ],
        )
        if account is None:
            await cq.answer("Клиент не найден", show_alert=True)
            return
        next_meeting = await session.scalar(
            select(Meeting)
            .where(Meeting.account_id == account_id, Meeting.starts_at >= now_utc())
            .order_by(Meeting.starts_at.asc())
            .limit(1)
        )

    open_deals = [d for d in account.deals if d.stage not in ("won", "lost")]
    open_tasks = [t for t in account.tasks if t.status in ("open", "in_progress")]

    lines = [
        ("🏦 " if account.type == "bank" else "🏢 ") + f"<b>{account.name}</b>",
    ]
    if account.industry:
        lines.append(f"Отрасль: {account.industry}")
    if account.owner:
        lines.append(f"Ответственный: {account.owner.name}")
    if open_deals:
        lines.append("\n<b>Сделки:</b>")
        for d in open_deals[:5]:
            amt = f" — {d.amount:,.0f} {d.currency}" if d.amount else ""
            lines.append(f"• {d.title} [{d.stage}]{amt}")
    if next_meeting:
        when = next_meeting.starts_at.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")
        lines.append(f"\n📅 Ближайшая встреча: {when} — {next_meeting.title}")
    if account.contacts:
        lines.append(f"\n👤 Контактов: {len(account.contacts)}")
    lines.append(f"✅ Открытых задач: {len(open_tasks)}")

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Задачи", callback_data=f"acc_tasks:{account_id}")
    kb.button(text="📅 Встречи", callback_data=f"acc_meet:{account_id}")
    kb.button(text="📝 Заметка", callback_data=f"acc_note:{account_id}")
    kb.button(text="➕ Задача", callback_data=f"acc_task:{account_id}")
    kb.button(text="🌐 Открыть в CRM", url=_crm_url(f"/accounts/{account_id}"))
    kb.adjust(2, 2, 1)

    await cq.message.answer("\n".join(lines), reply_markup=kb.as_markup())
    await cq.answer()


@dp.callback_query(F.data.startswith("acc_meet:"))
async def cb_account_meetings(cq: CallbackQuery):
    account_id = int(cq.data.split(":")[1])
    async with SessionLocal() as session:
        meetings = (
            await session.scalars(
                select(Meeting)
                .options(selectinload(Meeting.account))
                .where(
                    Meeting.account_id == account_id,
                    Meeting.starts_at >= now_utc() - timedelta(hours=1),
                )
                .order_by(Meeting.starts_at.asc())
                .limit(10)
            )
        ).all()
    await cq.message.answer(
        "<b>Предстоящие встречи</b>\n" + _fmt_meetings(meetings)
    )
    await cq.answer()


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #


def _task_kb(task: Task):
    kb = InlineKeyboardBuilder()
    kb.button(text="✓ Выполнено", callback_data=f"task_done:{task.id}")
    kb.button(text="▶ В работе", callback_data=f"task_prog:{task.id}")
    if task.linear_url:
        kb.button(text="Linear ↗", url=task.linear_url)
    kb.adjust(2, 1)
    return kb.as_markup()


async def _send_task_list(target: Message, account_id: int | None = None):
    async with SessionLocal() as session:
        stmt = (
            select(Task)
            .options(selectinload(Task.account))
            .where(Task.status.in_(["open", "in_progress"]))
            .order_by(Task.created_at.desc())
            .limit(15)
        )
        if account_id:
            stmt = stmt.where(Task.account_id == account_id)
        tasks = (await session.scalars(stmt)).all()

    if not tasks:
        await target.answer("Открытых задач нет 🎉")
        return
    await target.answer(f"<b>Открытые задачи ({len(tasks)})</b>")
    for t in tasks:
        mark = "▶" if t.status == "in_progress" else "•"
        text = f"{mark} <b>{t.title}</b>\n{t.account.name}"
        await target.answer(text, reply_markup=_task_kb(t))


@dp.message(Command("tasks"))
@dp.message(F.text == BTN_TASKS)
async def cmd_tasks(message: Message):
    async with SessionLocal() as session:
        if not await require_user(message, session):
            return
    await _send_task_list(message)


@dp.callback_query(F.data.startswith("acc_tasks:"))
async def cb_account_tasks(cq: CallbackQuery):
    account_id = int(cq.data.split(":")[1])
    await _send_task_list(cq.message, account_id=account_id)
    await cq.answer()


@dp.callback_query(F.data.startswith("task_done:"))
async def cb_task_done(cq: CallbackQuery):
    await _set_task_status(cq, int(cq.data.split(":")[1]), "done")


@dp.callback_query(F.data.startswith("task_prog:"))
async def cb_task_prog(cq: CallbackQuery):
    await _set_task_status(cq, int(cq.data.split(":")[1]), "in_progress")


async def _set_task_status(cq: CallbackQuery, task_id: int, status: str):
    async with SessionLocal() as session:
        task = await session.get(
            Task, task_id, options=[selectinload(Task.account)]
        )
        if task is None:
            await cq.answer("Задача не найдена", show_alert=True)
            return
        task.status = status
        await session.commit()
        label = "выполнена ✓" if status == "done" else "в работе ▶"
        title, account_name = task.title, task.account.name
    try:
        await cq.message.edit_text(f"<s>{title}</s>\n{account_name} — {label}")
    except Exception:  # noqa: BLE001 — message may be unchanged/old
        pass
    await cq.answer(f"Задача {label}")


# --------------------------------------------------------------------------- #
# Pipeline summary
# --------------------------------------------------------------------------- #


@dp.message(Command("deals"))
@dp.message(F.text == BTN_PIPELINE)
async def cmd_deals(message: Message):
    async with SessionLocal() as session:
        if not await require_user(message, session):
            return
        rows = (
            await session.execute(
                select(
                    Deal.stage,
                    func.count(Deal.id),
                    func.coalesce(func.sum(Deal.amount), 0),
                )
                .where(Deal.stage.not_in(["won", "lost"]))
                .group_by(Deal.stage)
            )
        ).all()
    if not rows:
        await message.answer("Активных сделок нет.")
        return
    order = {s: i for i, s in enumerate(
        ["lead", "qualified", "demo", "pilot", "procurement", "contract"]
    )}
    rows = sorted(rows, key=lambda r: order.get(r[0], 99))
    lines = ["<b>Воронка (активные сделки)</b>"]
    total = 0
    for stage, count, amount in rows:
        total += float(amount or 0)
        amt = f" — {float(amount):,.0f} ₽" if amount else ""
        lines.append(f"• {stage}: {count}{amt}")
    lines.append(f"\nИтого в работе: <b>{total:,.0f} ₽</b>")
    await message.answer("\n".join(lines))


# --------------------------------------------------------------------------- #
# FSM: add note / add task to a client
# --------------------------------------------------------------------------- #


@dp.callback_query(F.data.startswith("acc_note:"))
async def cb_add_note(cq: CallbackQuery, state: FSMContext):
    account_id = int(cq.data.split(":")[1])
    await state.set_state(Flow.note)
    await state.update_data(account_id=account_id)
    await cq.message.answer("📝 Введите текст заметки (или /cancel):")
    await cq.answer()


@dp.callback_query(F.data.startswith("acc_task:"))
async def cb_add_task(cq: CallbackQuery, state: FSMContext):
    account_id = int(cq.data.split(":")[1])
    await state.set_state(Flow.task)
    await state.update_data(account_id=account_id)
    await cq.message.answer("➕ Введите название задачи (или /cancel):")
    await cq.answer()


@dp.message(Command("cancel"), StateFilter(Flow.note, Flow.task))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


@dp.message(StateFilter(Flow.note), F.text)
async def fsm_save_note(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = data["account_id"]
    async with SessionLocal() as session:
        user = await _user(session, str(message.chat.id))
        log_activity(
            session,
            account_id=account_id,
            type="note",
            body=message.text.strip(),
            author_id=user.id if user else None,
        )
        await session.commit()
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="← К карточке", callback_data=f"acc:{account_id}")
    await message.answer("✅ Заметка сохранена.", reply_markup=kb.as_markup())


@dp.message(StateFilter(Flow.task), F.text)
async def fsm_save_task(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = data["account_id"]
    async with SessionLocal() as session:
        user = await _user(session, str(message.chat.id))
        account = await session.get(Account, account_id)
        task = await create_task_with_linear(
            session,
            account_id=account_id,
            title=message.text.strip(),
            source="manual",
            account_name=account.name if account else None,
            assignee_id=user.id if user else None,
        )
        log_activity(
            session,
            account_id=account_id,
            type="task",
            body=f"Задача создана: {task.title}",
            author_id=user.id if user else None,
            payload={"linear_url": task.linear_url} if task.linear_url else None,
        )
        await session.commit()
        linear_note = " (в Linear ↗)" if task.linear_url else ""
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="← К карточке", callback_data=f"acc:{account_id}")
    await message.answer(
        f"✅ Задача создана{linear_note}.", reply_markup=kb.as_markup()
    )


# --------------------------------------------------------------------------- #
# Free-text client search (default state, non-menu text)
# --------------------------------------------------------------------------- #


@dp.message(StateFilter(None), F.text)
async def text_search(message: Message):
    text = message.text.strip()
    if text in MENU_BUTTONS or text.startswith("/"):
        return
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        if len(text) < 2:
            await message.answer("Введите минимум 2 символа для поиска.")
            return
        like = f"%{text}%"
        accounts = (
            await session.scalars(
                select(Account)
                .where(or_(Account.name.ilike(like), Account.industry.ilike(like)))
                .order_by(Account.name)
                .limit(10)
            )
        ).all()
    if not accounts:
        await message.answer(f"По запросу «{text}» ничего не найдено.")
        return
    await message.answer(
        f"Найдено: {len(accounts)}", reply_markup=_clients_kb(accounts)
    )


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #


def build_bot() -> Bot:
    from aiogram.client.default import DefaultBotProperties

    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )


async def setup_bot_commands(bot: Bot) -> None:
    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(command="menu", description="Меню"),
            BotCommand(command="today", description="Встречи сегодня"),
            BotCommand(command="agenda", description="Встречи на неделю"),
            BotCommand(command="clients", description="Клиенты"),
            BotCommand(command="tasks", description="Открытые задачи"),
            BotCommand(command="deals", description="Воронка"),
            BotCommand(command="help", description="Помощь"),
        ]
    )
