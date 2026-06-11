from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Account, Activity, Meeting, Task
from app.security import User, require_login
from app.templating import render
from app.timeutil import now_utc

router = APIRouter()


@router.get("/")
async def dashboard(
    request: Request,
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    now = now_utc()
    horizon = now + timedelta(days=7)

    upcoming = (
        await session.scalars(
            select(Meeting)
            .options(selectinload(Meeting.account))
            .where(Meeting.starts_at >= now, Meeting.starts_at <= horizon)
            .order_by(Meeting.starts_at.asc())
            .limit(15)
        )
    ).all()

    open_tasks = (
        await session.scalars(
            select(Task)
            .options(selectinload(Task.account))
            .where(Task.status.in_(["open", "in_progress"]))
            .order_by(Task.created_at.desc())
            .limit(15)
        )
    ).all()

    recent = (
        await session.scalars(
            select(Activity)
            .options(selectinload(Activity.account))
            .order_by(Activity.created_at.desc())
            .limit(15)
        )
    ).all()

    counts = {
        "accounts": await session.scalar(select(func.count(Account.id))),
        "meetings": await session.scalar(
            select(func.count(Meeting.id)).where(Meeting.starts_at >= now)
        ),
        "open_tasks": await session.scalar(
            select(func.count(Task.id)).where(
                Task.status.in_(["open", "in_progress"])
            )
        ),
    }

    return render(
        request,
        "dashboard.html",
        user=user,
        upcoming=upcoming,
        open_tasks=open_tasks,
        recent=recent,
        counts=counts,
    )
