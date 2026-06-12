from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import TASK_STATUSES, Account, Deal, Task, User
from app.security import require_admin, require_member
from app.services.activities import log_activity
from app.services.linear import create_task_with_linear
from app.services.notifications import notify_task_assigned
from app.templating import render
from app.timeutil import now_utc, parse_local_dt

router = APIRouter(prefix="/tasks")


async def _users(session: AsyncSession) -> list[User]:
    return (await session.scalars(select(User).order_by(User.name))).all()


@router.get("")
async def tasks_list(
    request: Request,
    status: str = "active",
    mine: str = "",
    user: User = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Task)
        .options(selectinload(Task.account), selectinload(Task.assignee))
        .order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.created_at.desc())
    )
    if status == "active":
        stmt = stmt.where(Task.status.in_(["open", "in_progress"]))
    elif status in TASK_STATUSES:
        stmt = stmt.where(Task.status == status)
    if mine == "1":
        stmt = stmt.where(Task.assignee_id == user.id)
    tasks = (await session.scalars(stmt)).all()
    return render(
        request,
        "tasks/list.html",
        user=user,
        tasks=tasks,
        status=status,
        mine=mine,
        now=now_utc(),
    )


@router.get("/new")
async def new_task_form(
    request: Request,
    account_id: int | None = None,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    accounts = (
        await session.scalars(select(Account).order_by(Account.name))
    ).all()
    return render(
        request,
        "tasks/form.html",
        user=user,
        task=None,
        accounts=accounts,
        users=await _users(session),
        deals=[],
        preselect_account=account_id,
    )


@router.post("")
async def create_task(
    request: Request,
    account_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    assignee_id: str = Form(""),
    due_date: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    account = await session.get(Account, account_id)
    if account is None:
        return RedirectResponse(url="/tasks", status_code=303)
    aid = int(assignee_id) if assignee_id else None
    task = await create_task_with_linear(
        session,
        account_id=account_id,
        title=title.strip(),
        description=description.strip() or None,
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


@router.get("/{task_id}/edit")
async def edit_task_form(
    request: Request,
    task_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(
        Task, task_id, options=[selectinload(Task.account)]
    )
    if task is None:
        return render(request, "404.html", user=user, status_code=404)
    deals = (
        await session.scalars(
            select(Deal).where(Deal.account_id == task.account_id)
        )
    ).all()
    return render(
        request,
        "tasks/form.html",
        user=user,
        task=task,
        accounts=[task.account],
        users=await _users(session),
        deals=deals,
        preselect_account=task.account_id,
    )


@router.post("/{task_id}/edit")
async def edit_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("open"),
    assignee_id: str = Form(""),
    deal_id: str = Form(""),
    due_date: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(
        Task, task_id, options=[selectinload(Task.account)]
    )
    if task is None:
        return render(request, "404.html", user=user, status_code=404)
    prev_assignee = task.assignee_id
    new_assignee = int(assignee_id) if assignee_id else None
    task.title = title.strip()
    task.description = description.strip() or None
    task.status = status if status in TASK_STATUSES else task.status
    task.assignee_id = new_assignee
    task.deal_id = int(deal_id) if deal_id.strip() else None
    task.due_date = parse_local_dt(due_date)
    await session.commit()
    if new_assignee and new_assignee != prev_assignee:
        assignee = await session.get(User, new_assignee)
        await notify_task_assigned(assignee, task, task.account.name)
    return RedirectResponse(
        url=f"/accounts/{task.account_id}#tasks", status_code=303
    )


@router.post("/{task_id}/status")
async def update_status(
    task_id: int,
    status: str = Form(...),
    redirect: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(Task, task_id)
    if task is None:
        return RedirectResponse(url="/tasks", status_code=303)
    if status in TASK_STATUSES:
        task.status = status
        await session.commit()
    return RedirectResponse(url=redirect or "/tasks", status_code=303)


@router.post("/{task_id}/delete")
async def delete_task(
    task_id: int,
    redirect: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(Task, task_id)
    if task is not None:
        await session.delete(task)
        await session.commit()
    return RedirectResponse(url=redirect or "/tasks", status_code=303)
