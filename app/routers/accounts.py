from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Account, Activity, Contact, Deal, Meeting, Task, User
from app.security import require_admin, require_member
from app.services.activities import log_activity
from app.services.linear import create_task_with_linear
from app.services.notifications import notify_task_assigned
from app.templating import render
from app.timeutil import now_utc, parse_local_dt

router = APIRouter(prefix="/accounts")


async def _load_users(session: AsyncSession) -> list[User]:
    return (await session.scalars(select(User).order_by(User.name))).all()


async def _get_account(session: AsyncSession, account_id: int) -> Account | None:
    return await session.get(
        Account,
        account_id,
        options=[
            selectinload(Account.owner),
            selectinload(Account.contacts),
            selectinload(Account.deals),
            selectinload(Account.meetings).selectinload(Meeting.owner),
            selectinload(Account.tasks).selectinload(Task.assignee),
        ],
    )


@router.get("")
async def list_accounts(
    request: Request,
    q: str = "",
    user: User = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Account)
        .options(selectinload(Account.owner))
        .order_by(Account.created_at.desc())
    )
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Account.name.ilike(like), Account.industry.ilike(like))
        )
    accounts = (await session.scalars(stmt)).all()
    return render(
        request, "accounts/list.html", user=user, accounts=accounts, q=q
    )


@router.get("/new")
async def new_account_form(
    request: Request,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    users = await _load_users(session)
    return render(
        request, "accounts/form.html", user=user, users=users, account=None
    )


@router.post("")
async def create_account(
    request: Request,
    name: str = Form(...),
    type: str = Form("company"),
    industry: str = Form(""),
    website: str = Form(""),
    notes: str = Form(""),
    owner_id: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    account = Account(
        name=name.strip(),
        type=type,
        industry=industry.strip() or None,
        website=website.strip() or None,
        notes=notes.strip() or None,
        owner_id=int(owner_id) if owner_id else user.id,
    )
    session.add(account)
    await session.flush()
    log_activity(
        session,
        account_id=account.id,
        type="note",
        body="Клиент создан",
        author_id=user.id,
    )
    await session.commit()
    return RedirectResponse(url=f"/accounts/{account.id}", status_code=303)


@router.get("/{account_id}")
async def account_detail(
    request: Request,
    account_id: int,
    user: User = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    account = await _get_account(session, account_id)
    if account is None:
        return render(request, "404.html", user=user, status_code=404)

    activities = (
        await session.scalars(
            select(Activity)
            .options(selectinload(Activity.account))
            .where(Activity.account_id == account_id)
            .order_by(Activity.created_at.desc())
            .limit(50)
        )
    ).all()

    # Sort children for stable display.
    deals = sorted(account.deals, key=lambda d: d.created_at, reverse=True)
    meetings = sorted(account.meetings, key=lambda m: m.starts_at, reverse=True)
    tasks = sorted(account.tasks, key=lambda t: t.created_at, reverse=True)

    return render(
        request,
        "accounts/detail.html",
        user=user,
        account=account,
        activities=activities,
        deals=deals,
        meetings=meetings,
        tasks=tasks,
        users=await _load_users(session),
        now=now_utc(),
    )


@router.get("/{account_id}/edit")
async def edit_account_form(
    request: Request,
    account_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    account = await session.get(Account, account_id)
    if account is None:
        return render(request, "404.html", user=user, status_code=404)
    users = await _load_users(session)
    return render(
        request, "accounts/form.html", user=user, users=users, account=account
    )


@router.post("/{account_id}/edit")
async def edit_account(
    request: Request,
    account_id: int,
    name: str = Form(...),
    type: str = Form("company"),
    industry: str = Form(""),
    website: str = Form(""),
    notes: str = Form(""),
    owner_id: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    account = await session.get(Account, account_id)
    if account is None:
        return render(request, "404.html", user=user, status_code=404)
    account.name = name.strip()
    account.type = type
    account.industry = industry.strip() or None
    account.website = website.strip() or None
    account.notes = notes.strip() or None
    account.owner_id = int(owner_id) if owner_id else None
    await session.commit()
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@router.post("/{account_id}/delete")
async def delete_account(
    account_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    account = await session.get(Account, account_id)
    if account is not None:
        await session.delete(account)
        await session.commit()
    return RedirectResponse(url="/accounts", status_code=303)


@router.post("/{account_id}/contacts")
async def add_contact(
    account_id: int,
    name: str = Form(...),
    position: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    telegram: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    session.add(
        Contact(
            account_id=account_id,
            name=name.strip(),
            position=position.strip() or None,
            email=email.strip() or None,
            phone=phone.strip() or None,
            telegram=telegram.strip() or None,
        )
    )
    await session.commit()
    return RedirectResponse(url=f"/accounts/{account_id}#contacts", status_code=303)


@router.post("/{account_id}/activities")
async def add_activity(
    account_id: int,
    type: str = Form("note"),
    body: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    log_activity(
        session,
        account_id=account_id,
        type=type,
        body=body.strip() or None,
        author_id=user.id,
    )
    await session.commit()
    return RedirectResponse(url=f"/accounts/{account_id}#activity", status_code=303)


@router.post("/{account_id}/deals")
async def add_deal(
    account_id: int,
    title: str = Form(...),
    stage: str = Form("lead"),
    amount: str = Form(""),
    currency: str = Form("RUB"),
    probability: str = Form("0"),
    expected_close: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    deal = Deal(
        account_id=account_id,
        title=title.strip(),
        stage=stage,
        amount=float(amount) if amount.strip() else None,
        currency=currency or "RUB",
        probability=int(probability) if probability.strip().isdigit() else 0,
        owner_id=user.id,
        expected_close=parse_local_dt(expected_close),
    )
    session.add(deal)
    log_activity(
        session,
        account_id=account_id,
        type="stage_change",
        body=f"Сделка «{deal.title}» создана на этапе {stage}",
        author_id=user.id,
    )
    await session.commit()
    return RedirectResponse(url=f"/accounts/{account_id}#deals", status_code=303)


@router.post("/{account_id}/tasks")
async def add_task(
    account_id: int,
    title: str = Form(...),
    description: str = Form(""),
    deal_id: str = Form(""),
    assignee_id: str = Form(""),
    due_date: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    account = await session.get(Account, account_id)
    if account is None:
        return RedirectResponse(url="/accounts", status_code=303)
    aid = int(assignee_id) if assignee_id else None
    task = await create_task_with_linear(
        session,
        account_id=account_id,
        title=title.strip(),
        description=description.strip() or None,
        deal_id=int(deal_id) if deal_id.strip() else None,
        assignee_id=aid,
        due_date=parse_local_dt(due_date),
        source="manual",
        account_name=account.name,
    )
    log_activity(
        session,
        account_id=account_id,
        type="task",
        body=f"Задача создана: {task.title}",
        author_id=user.id,
        payload={"linear_url": task.linear_url} if task.linear_url else None,
    )
    await session.commit()
    if aid:
        assignee = await session.get(User, aid)
        await notify_task_assigned(assignee, task, account.name)
    return RedirectResponse(url=f"/accounts/{account_id}#tasks", status_code=303)
