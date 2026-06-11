from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import TASK_STATUSES, Task, User
from app.security import require_login, require_role
from app.templating import render

router = APIRouter(prefix="/tasks")


@router.get("")
async def tasks_list(
    request: Request,
    status: str = "active",
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Task)
        .options(selectinload(Task.account))
        .order_by(Task.created_at.desc())
    )
    if status == "active":
        stmt = stmt.where(Task.status.in_(["open", "in_progress"]))
    elif status in TASK_STATUSES:
        stmt = stmt.where(Task.status == status)
    tasks = (await session.scalars(stmt)).all()
    return render(
        request, "tasks/list.html", user=user, tasks=tasks, status=status
    )


@router.post("/{task_id}/status")
async def update_status(
    task_id: int,
    status: str = Form(...),
    redirect: str = Form(""),
    user: User = Depends(require_role("manager")),
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
    user: User = Depends(require_role("manager")),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(Task, task_id)
    if task is not None:
        await session.delete(task)
        await session.commit()
    return RedirectResponse(url=redirect or "/tasks", status_code=303)
