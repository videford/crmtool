from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Account, Meeting, User
from app.security import require_admin, require_member
from app.services.activities import log_activity
from app.services.notifications import notify_meeting_assigned
from app.templating import render
from app.timeutil import now_utc, parse_local_dt

router = APIRouter(prefix="/meetings")


async def _users(session: AsyncSession) -> list[User]:
    return (await session.scalars(select(User).order_by(User.name))).all()


@router.get("")
async def meetings_list(
    request: Request,
    scope: str = "upcoming",
    mine: str = "",
    user: User = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    now = now_utc()
    stmt = select(Meeting).options(
        selectinload(Meeting.account), selectinload(Meeting.owner)
    )
    if scope == "past":
        stmt = stmt.where(Meeting.starts_at < now).order_by(
            Meeting.starts_at.desc()
        )
    else:
        stmt = stmt.where(Meeting.starts_at >= now - timedelta(hours=1)).order_by(
            Meeting.starts_at.asc()
        )
    if mine == "1":
        stmt = stmt.where(Meeting.owner_id == user.id)
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
        users=await _users(session),
        scope=scope,
        mine=mine,
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
    owner_id: str = Form(""),
    redirect: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    starts = parse_local_dt(starts_at)
    if starts is None:
        return RedirectResponse(url=redirect or "/meetings", status_code=303)
    oid = int(owner_id) if owner_id else user.id
    meeting = Meeting(
        account_id=account_id,
        deal_id=int(deal_id) if deal_id.strip() else None,
        title=title.strip(),
        starts_at=starts,
        ends_at=parse_local_dt(ends_at),
        location=location.strip() or None,
        participants=participants.strip() or None,
        owner_id=oid,
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
    if oid and oid != user.id:
        owner = await session.get(User, oid)
        account = await session.get(Account, account_id)
        await notify_meeting_assigned(
            owner, meeting, account.name if account else None
        )
    return RedirectResponse(
        url=redirect or f"/accounts/{account_id}#meetings", status_code=303
    )


@router.get("/{meeting_id}/edit")
async def edit_meeting_form(
    request: Request,
    meeting_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    meeting = await session.get(
        Meeting, meeting_id, options=[selectinload(Meeting.account)]
    )
    if meeting is None:
        return render(request, "404.html", user=user, status_code=404)
    return render(
        request,
        "meetings/form.html",
        user=user,
        meeting=meeting,
        users=await _users(session),
    )


@router.post("/{meeting_id}/edit")
async def edit_meeting(
    meeting_id: int,
    title: str = Form(...),
    starts_at: str = Form(...),
    ends_at: str = Form(""),
    location: str = Form(""),
    participants: str = Form(""),
    owner_id: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None:
        return RedirectResponse(url="/meetings", status_code=303)
    starts = parse_local_dt(starts_at)
    rescheduled = starts is not None and starts != meeting.starts_at
    prev_owner = meeting.owner_id
    new_owner = int(owner_id) if owner_id else None
    if starts is not None:
        meeting.starts_at = starts
    meeting.title = title.strip()
    meeting.ends_at = parse_local_dt(ends_at)
    meeting.location = location.strip() or None
    meeting.participants = participants.strip() or None
    meeting.owner_id = new_owner
    if rescheduled:
        # Allow reminders to fire again for the new time.
        meeting.reminded_offsets = []
    await session.commit()
    if new_owner and new_owner != prev_owner and new_owner != user.id:
        owner = await session.get(User, new_owner)
        account = await session.get(Account, meeting.account_id)
        await notify_meeting_assigned(
            owner, meeting, account.name if account else None
        )
    return RedirectResponse(
        url=f"/accounts/{meeting.account_id}#meetings", status_code=303
    )


@router.post("/{meeting_id}/delete")
async def delete_meeting(
    meeting_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    meeting = await session.get(Meeting, meeting_id)
    account_id = meeting.account_id if meeting else None
    if meeting is not None:
        await session.delete(meeting)
        await session.commit()
    target = f"/accounts/{account_id}#meetings" if account_id else "/meetings"
    return RedirectResponse(url=target, status_code=303)
