from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Account, Meeting, User
from app.security import require_login, require_role
from app.services.activities import log_activity
from app.templating import render
from app.timeutil import now_utc, parse_local_dt

router = APIRouter(prefix="/meetings")


@router.get("")
async def meetings_list(
    request: Request,
    scope: str = "upcoming",
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    now = now_utc()
    stmt = select(Meeting).options(selectinload(Meeting.account))
    if scope == "past":
        stmt = stmt.where(Meeting.starts_at < now).order_by(
            Meeting.starts_at.desc()
        )
    else:
        stmt = stmt.where(Meeting.starts_at >= now - timedelta(hours=1)).order_by(
            Meeting.starts_at.asc()
        )
    meetings = (await session.scalars(stmt)).all()
    accounts = (
        await session.scalars(select(Account).order_by(Account.name))
    ).all()
    return render(
        request,
        "meetings/list.html",
        user=user,
        meetings=meetings,
        accounts=accounts,
        scope=scope,
    )


@router.post("")
async def create_meeting(
    account_id: int = Form(...),
    title: str = Form(...),
    starts_at: str = Form(...),
    ends_at: str = Form(""),
    location: str = Form(""),
    participants: str = Form(""),
    deal_id: str = Form(""),
    redirect: str = Form(""),
    user: User = Depends(require_role("manager")),
    session: AsyncSession = Depends(get_session),
):
    starts = parse_local_dt(starts_at)
    if starts is None:
        return RedirectResponse(url=redirect or "/meetings", status_code=303)
    meeting = Meeting(
        account_id=account_id,
        deal_id=int(deal_id) if deal_id.strip() else None,
        title=title.strip(),
        starts_at=starts,
        ends_at=parse_local_dt(ends_at),
        location=location.strip() or None,
        participants=participants.strip() or None,
        owner_id=user.id,
        reminded_offsets=[],
    )
    session.add(meeting)
    log_activity(
        session,
        account_id=account_id,
        type="meeting",
        body=f"Встреча запланирована: {meeting.title}",
        author_id=user.id,
    )
    await session.commit()
    return RedirectResponse(
        url=redirect or f"/accounts/{account_id}#meetings", status_code=303
    )


@router.post("/{meeting_id}/edit")
async def edit_meeting(
    meeting_id: int,
    title: str = Form(...),
    starts_at: str = Form(...),
    ends_at: str = Form(""),
    location: str = Form(""),
    participants: str = Form(""),
    user: User = Depends(require_role("manager")),
    session: AsyncSession = Depends(get_session),
):
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None:
        return RedirectResponse(url="/meetings", status_code=303)
    starts = parse_local_dt(starts_at)
    rescheduled = starts is not None and starts != meeting.starts_at
    if starts is not None:
        meeting.starts_at = starts
    meeting.title = title.strip()
    meeting.ends_at = parse_local_dt(ends_at)
    meeting.location = location.strip() or None
    meeting.participants = participants.strip() or None
    if rescheduled:
        # Allow reminders to fire again for the new time.
        meeting.reminded_offsets = []
    await session.commit()
    return RedirectResponse(
        url=f"/accounts/{meeting.account_id}#meetings", status_code=303
    )


@router.post("/{meeting_id}/delete")
async def delete_meeting(
    meeting_id: int,
    user: User = Depends(require_role("manager")),
    session: AsyncSession = Depends(get_session),
):
    meeting = await session.get(Meeting, meeting_id)
    account_id = meeting.account_id if meeting else None
    if meeting is not None:
        await session.delete(meeting)
        await session.commit()
    target = f"/accounts/{account_id}#meetings" if account_id else "/meetings"
    return RedirectResponse(url=target, status_code=303)
