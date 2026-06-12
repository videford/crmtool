from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import DEAL_STAGES, Account, Activity, Deal, Meeting, Task
from app.security import User, require_member
from app.templating import render
from app.timeutil import now_utc

router = APIRouter()


@router.get("/")
async def dashboard(
    request: Request,
    user: User = Depends(require_member),
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
            .options(selectinload(Task.account), selectinload(Task.assignee))
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

    open_stages = [s for s in DEAL_STAGES if s not in ("won", "lost")]
    pipeline = {
        "open_value": await session.scalar(
            select(func.coalesce(func.sum(Deal.amount), 0)).where(
                Deal.stage.in_(open_stages)
            )
        ),
        "weighted": await session.scalar(
            select(
                func.coalesce(func.sum(Deal.amount * Deal.probability / 100.0), 0)
            ).where(Deal.stage.in_(open_stages))
        ),
        "won_value": await session.scalar(
            select(func.coalesce(func.sum(Deal.amount), 0)).where(
                Deal.stage == "won"
            )
        ),
    }

    stage_rows = (
        await session.execute(
            select(
                Deal.stage,
                func.count(Deal.id),
                func.coalesce(func.sum(Deal.amount), 0),
            )
            .where(Deal.stage.in_(open_stages))
            .group_by(Deal.stage)
        )
    ).all()
    by_stage_map = {r[0]: (r[1], float(r[2])) for r in stage_rows}
    by_stage = [
        {"stage": s, "count": by_stage_map.get(s, (0, 0))[0],
         "value": by_stage_map.get(s, (0, 0))[1]}
        for s in open_stages
    ]
    max_stage_value = max([s["value"] for s in by_stage] + [1])

    return render(
        request,
        "dashboard.html",
        user=user,
        upcoming=upcoming,
        open_tasks=open_tasks,
        recent=recent,
        counts=counts,
        pipeline=pipeline,
        by_stage=by_stage,
        max_stage_value=max_stage_value,
    )
