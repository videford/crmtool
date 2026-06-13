"""aiogram bot: rich CRM control from Telegram, trilingual (ru/uz/en).

Runs in polling mode inside the worker process (see worker/main.py).
Language is per-user (User.language) and switchable with /language.
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
from app.i18n import LANGUAGE_NAMES, LANGUAGES, normalize_lang
from app.i18n import t as _t
from app.models import Account, Deal, Meeting, Task, User
from app.services.activities import log_activity
from app.services.linear import create_task_with_linear
from app.timeutil import LOCAL_TZ, now_utc

dp = Dispatcher()

# Localized reply-keyboard labels, and the set of all variants per action so
# handlers match whichever language the user's keyboard is in.
CLIENTS_LABELS = {_t(l, "bot.menu_clients") for l in LANGUAGES}
MEETINGS_LABELS = {_t(l, "bot.menu_meetings") for l in LANGUAGES}
TASKS_LABELS = {_t(l, "bot.menu_tasks") for l in LANGUAGES}
PIPELINE_LABELS = {_t(l, "bot.menu_pipeline") for l in LANGUAGES}
MENU_BUTTONS = CLIENTS_LABELS | MEETINGS_LABELS | TASKS_LABELS | PIPELINE_LABELS


class Flow(StatesGroup):
    note = State()
    task = State()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def main_menu(lang: str):
    kb = ReplyKeyboardBuilder()
    kb.button(text=_t(lang, "bot.menu_clients"))
    kb.button(text=_t(lang, "bot.menu_meetings"))
    kb.button(text=_t(lang, "bot.menu_tasks"))
    kb.button(text=_t(lang, "bot.menu_pipeline"))
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


def tg_lang(message: Message) -> str:
    """Best-effort language for users who aren't linked yet."""
    code = (message.from_user.language_code or "")[:2] if message.from_user else ""
    return normalize_lang(code)


async def _user(session, chat_id: str) -> User | None:
    return await session.scalar(
        select(User).where(User.telegram_chat_id == chat_id)
    )


async def _lang(session, chat_id: str) -> str:
    user = await _user(session, chat_id)
    return normalize_lang(user.language) if user else "ru"


def _site_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=_t(lang, "bot.open_site"), url=settings.base_url or "https://example.com")
    return kb.as_markup()


async def _ask_to_register(message: Message) -> None:
    lang = tg_lang(message)
    text = (
        _t(lang, "bot.not_linked")
        + "\n\n"
        + _t(lang, "bot.register_prompt", url=settings.base_url)
    )
    await message.answer(text, reply_markup=_site_kb(lang))


async def require_user(message: Message, session) -> User | None:
    user = await _user(session, str(message.chat.id))
    if user is None:
        await _ask_to_register(message)
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
            lang = normalize_lang(linked.language)
            await message.answer(
                _t(lang, "bot.welcome_back", name=linked.name),
                reply_markup=main_menu(lang),
            )
            return
        if not code:
            lang = tg_lang(message)
            await message.answer(
                _t(lang, "bot.link_hint")
                + "\n\n"
                + _t(lang, "bot.register_prompt", url=settings.base_url),
                reply_markup=_site_kb(lang),
            )
            return
        user = await session.scalar(
            select(User).where(User.telegram_link_code == code)
        )
        if user is None:
            await message.answer(_t(tg_lang(message), "bot.code_not_found"))
            return
        user.telegram_chat_id = chat_id
        user.telegram_link_code = None
        await session.commit()
        lang = normalize_lang(user.language)
        await message.answer(
            _t(lang, "bot.linked_ok", name=user.name) + "\n" + _t(lang, "bot.commands_hint"),
            reply_markup=main_menu(lang),
        )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    async with SessionLocal() as session:
        lang = await _lang(session, str(message.chat.id))
    await message.answer(_t(lang, "bot.help"), reply_markup=main_menu(lang))


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    async with SessionLocal() as session:
        lang = await _lang(session, str(message.chat.id))
    await message.answer(_t(lang, "bot.menu"), reply_markup=main_menu(lang))


# --------------------------------------------------------------------------- #
# Language
# --------------------------------------------------------------------------- #


@dp.message(Command("language"))
async def cmd_language(message: Message):
    async with SessionLocal() as session:
        lang = await _lang(session, str(message.chat.id))
    kb = InlineKeyboardBuilder()
    for code in LANGUAGES:
        kb.button(text=LANGUAGE_NAMES[code], callback_data=f"setlang:{code}")
    kb.adjust(3)
    await message.answer(_t(lang, "bot.choose_language"), reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("setlang:"))
async def cb_set_language(cq: CallbackQuery):
    code = normalize_lang(cq.data.split(":")[1])
    async with SessionLocal() as session:
        user = await _user(session, str(cq.message.chat.id))
        if user is not None:
            user.language = code
            await session.commit()
    await cq.message.answer(_t(code, "bot.language_set"), reply_markup=main_menu(code))
    await cq.answer()


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


def _fmt_meetings(meetings: list[Meeting], lang: str) -> str:
    if not meetings:
        return _t(lang, "bot.no_meetings")
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
        lang = normalize_lang(user.language)
        meetings = await _meetings_for(session, user, until_days=1)
        today = now_utc().astimezone(LOCAL_TZ).date()
        meetings = [
            m for m in meetings if m.starts_at.astimezone(LOCAL_TZ).date() == today
        ]
        await message.answer(
            f"<b>{_t(lang, 'bot.today')}</b>\n" + _fmt_meetings(meetings, lang)
        )


@dp.message(Command("agenda"))
@dp.message(F.text.in_(MEETINGS_LABELS))
async def cmd_agenda(message: Message):
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        lang = normalize_lang(user.language)
        meetings = await _meetings_for(session, user, until_days=7)
        await message.answer(
            f"<b>{_t(lang, 'bot.agenda')}</b>\n" + _fmt_meetings(meetings, lang)
        )


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
@dp.message(F.text.in_(CLIENTS_LABELS))
async def cmd_clients(message: Message):
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        lang = normalize_lang(user.language)
        accounts = (
            await session.scalars(
                select(Account).order_by(Account.created_at.desc()).limit(10)
            )
        ).all()
        if not accounts:
            await message.answer(_t(lang, "bot.no_clients"))
            return
        await message.answer(
            f"<b>{_t(lang, 'bot.recent_clients')}</b>\n{_t(lang, 'bot.search_hint')}",
            reply_markup=_clients_kb(accounts),
        )


@dp.callback_query(F.data.startswith("acc:"))
async def cb_account_card(cq: CallbackQuery):
    account_id = int(cq.data.split(":")[1])
    async with SessionLocal() as session:
        lang = await _lang(session, str(cq.message.chat.id))
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
            await cq.answer(_t(lang, "bot.client_not_found"), show_alert=True)
            return
        next_meeting = await session.scalar(
            select(Meeting)
            .where(Meeting.account_id == account_id, Meeting.starts_at >= now_utc())
            .order_by(Meeting.starts_at.asc())
            .limit(1)
        )

    open_deals = [d for d in account.deals if d.stage not in ("won", "lost")]
    open_tasks = [t for t in account.tasks if t.status in ("open", "in_progress")]

    lines = [("🏦 " if account.type == "bank" else "🏢 ") + f"<b>{account.name}</b>"]
    if account.industry:
        lines.append(f"{_t(lang, 'bot.industry')}: {account.industry}")
    if account.owner:
        lines.append(f"{_t(lang, 'bot.owner')}: {account.owner.name}")
    if open_deals:
        lines.append(f"\n<b>{_t(lang, 'bot.deals')}:</b>")
        for d in open_deals[:5]:
            amt = f" — {d.amount:,.0f} {settings.currency_symbol}" if d.amount else ""
            lines.append(f"• {d.title} [{_t(lang, 'stage.' + d.stage)}]{amt}")
    if next_meeting:
        when = next_meeting.starts_at.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")
        lines.append(f"\n📅 {_t(lang, 'bot.next_meeting')}: {when} — {next_meeting.title}")
    if account.contacts:
        lines.append(f"\n👤 {_t(lang, 'bot.contacts_count')}: {len(account.contacts)}")
    lines.append(f"✅ {_t(lang, 'bot.open_tasks_count')}: {len(open_tasks)}")

    kb = InlineKeyboardBuilder()
    kb.button(text=_t(lang, "bot.btn_tasks"), callback_data=f"acc_tasks:{account_id}")
    kb.button(text=_t(lang, "bot.btn_meetings"), callback_data=f"acc_meet:{account_id}")
    kb.button(text=_t(lang, "bot.btn_note"), callback_data=f"acc_note:{account_id}")
    kb.button(text=_t(lang, "bot.btn_task"), callback_data=f"acc_task:{account_id}")
    kb.button(text=_t(lang, "bot.open_in_crm"), url=_crm_url(f"/accounts/{account_id}"))
    kb.adjust(2, 2, 1)

    await cq.message.answer("\n".join(lines), reply_markup=kb.as_markup())
    await cq.answer()


@dp.callback_query(F.data.startswith("acc_meet:"))
async def cb_account_meetings(cq: CallbackQuery):
    account_id = int(cq.data.split(":")[1])
    async with SessionLocal() as session:
        lang = await _lang(session, str(cq.message.chat.id))
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
        f"<b>{_t(lang, 'bot.upcoming_meetings')}</b>\n" + _fmt_meetings(meetings, lang)
    )
    await cq.answer()


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #


def _task_kb(task: Task, lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=_t(lang, "bot.btn_done"), callback_data=f"task_done:{task.id}")
    kb.button(text=_t(lang, "bot.btn_prog"), callback_data=f"task_prog:{task.id}")
    if task.linear_url:
        kb.button(text="Linear ↗", url=task.linear_url)
    kb.adjust(2, 1)
    return kb.as_markup()


async def _send_task_list(target: Message, account_id: int | None = None):
    async with SessionLocal() as session:
        lang = await _lang(session, str(target.chat.id))
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
        await target.answer(_t(lang, "bot.tasks_done_zero"))
        return
    await target.answer(f"<b>{_t(lang, 'bot.open_tasks')} ({len(tasks)})</b>")
    for task in tasks:
        mark = "▶" if task.status == "in_progress" else "•"
        text = f"{mark} <b>{task.title}</b>\n{task.account.name}"
        await target.answer(text, reply_markup=_task_kb(task, lang))


@dp.message(Command("tasks"))
@dp.message(F.text.in_(TASKS_LABELS))
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
        lang = await _lang(session, str(cq.message.chat.id))
        task = await session.get(
            Task, task_id, options=[selectinload(Task.account)]
        )
        if task is None:
            await cq.answer(_t(lang, "bot.task_not_found"), show_alert=True)
            return
        task.status = status
        await session.commit()
        label = _t(lang, "bot.label_done" if status == "done" else "bot.label_prog")
        title, account_name = task.title, task.account.name
    try:
        await cq.message.edit_text(f"<s>{title}</s>\n{account_name} — {label}")
    except Exception:  # noqa: BLE001 — message may be unchanged/old
        pass
    await cq.answer(_t(lang, "bot.task_status_changed", label=label))


# --------------------------------------------------------------------------- #
# Pipeline summary
# --------------------------------------------------------------------------- #


@dp.message(Command("deals"))
@dp.message(F.text.in_(PIPELINE_LABELS))
async def cmd_deals(message: Message):
    async with SessionLocal() as session:
        user = await require_user(message, session)
        if not user:
            return
        lang = normalize_lang(user.language)
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
        await message.answer(_t(lang, "bot.no_active_deals"))
        return
    order = {s: i for i, s in enumerate(
        ["lead", "qualified", "demo", "pilot", "procurement", "contract"]
    )}
    rows = sorted(rows, key=lambda r: order.get(r[0], 99))
    lines = [f"<b>{_t(lang, 'bot.pipeline')}</b>"]
    total = 0
    for stage, count, amount in rows:
        total += float(amount or 0)
        amt = f" — {float(amount):,.0f} {settings.currency_symbol}" if amount else ""
        lines.append(f"• {_t(lang, 'stage.' + stage)}: {count}{amt}")
    lines.append(f"\n{_t(lang, 'bot.total_in_work')}: <b>{total:,.0f} {settings.currency_symbol}</b>")
    await message.answer("\n".join(lines))


# --------------------------------------------------------------------------- #
# FSM: add note / add task to a client
# --------------------------------------------------------------------------- #


@dp.callback_query(F.data.startswith("acc_note:"))
async def cb_add_note(cq: CallbackQuery, state: FSMContext):
    account_id = int(cq.data.split(":")[1])
    async with SessionLocal() as session:
        lang = await _lang(session, str(cq.message.chat.id))
    await state.set_state(Flow.note)
    await state.update_data(account_id=account_id)
    await cq.message.answer(_t(lang, "bot.note_prompt"))
    await cq.answer()


@dp.callback_query(F.data.startswith("acc_task:"))
async def cb_add_task(cq: CallbackQuery, state: FSMContext):
    account_id = int(cq.data.split(":")[1])
    async with SessionLocal() as session:
        lang = await _lang(session, str(cq.message.chat.id))
    await state.set_state(Flow.task)
    await state.update_data(account_id=account_id)
    await cq.message.answer(_t(lang, "bot.task_prompt"))
    await cq.answer()


@dp.message(Command("cancel"), StateFilter(Flow.note, Flow.task))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        lang = await _lang(session, str(message.chat.id))
    await message.answer(_t(lang, "bot.canceled"), reply_markup=main_menu(lang))


@dp.message(StateFilter(Flow.note), F.text)
async def fsm_save_note(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = data["account_id"]
    async with SessionLocal() as session:
        user = await _user(session, str(message.chat.id))
        lang = normalize_lang(user.language) if user else "ru"
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
    kb.button(text=_t(lang, "bot.back_to_card"), callback_data=f"acc:{account_id}")
    await message.answer(_t(lang, "bot.note_saved"), reply_markup=kb.as_markup())


@dp.message(StateFilter(Flow.task), F.text)
async def fsm_save_task(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = data["account_id"]
    async with SessionLocal() as session:
        user = await _user(session, str(message.chat.id))
        lang = normalize_lang(user.language) if user else "ru"
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
        linear_note = _t(lang, "bot.in_linear_short") if task.linear_url else ""
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text=_t(lang, "bot.back_to_card"), callback_data=f"acc:{account_id}")
    await message.answer(
        _t(lang, "bot.task_created", linear=linear_note), reply_markup=kb.as_markup()
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
        lang = normalize_lang(user.language)
        if len(text) < 2:
            await message.answer(_t(lang, "bot.min_chars"))
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
        await message.answer(_t(lang, "bot.nothing_found", q=text))
        return
    await message.answer(
        _t(lang, "bot.found", n=len(accounts)), reply_markup=_clients_kb(accounts)
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
            BotCommand(command="menu", description="Menu / Меню / Menyu"),
            BotCommand(command="today", description="Today / Сегодня / Bugun"),
            BotCommand(command="agenda", description="Week / Неделя / Hafta"),
            BotCommand(command="clients", description="Clients / Клиенты / Mijozlar"),
            BotCommand(command="tasks", description="Tasks / Задачи / Vazifalar"),
            BotCommand(command="deals", description="Pipeline / Воронка / Voronka"),
            BotCommand(command="language", description="Language / Язык / Til"),
            BotCommand(command="help", description="Help / Помощь / Yordam"),
        ]
    )
