from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.security import (
    hash_password,
    new_link_code,
    require_login,
    require_role,
)
from app.templating import render

router = APIRouter(prefix="/settings")


@router.get("")
async def settings_page(
    request: Request,
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    users = []
    if user.role == "admin":
        users = (await session.scalars(select(User).order_by(User.name))).all()
    return render(request, "settings.html", user=user, users=users)


@router.post("/telegram/regenerate")
async def regenerate_link_code(
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    db_user = await session.get(User, user.id)
    db_user.telegram_link_code = new_link_code()
    await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/telegram/unlink")
async def unlink_telegram(
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    db_user = await session.get(User, user.id)
    db_user.telegram_chat_id = None
    db_user.telegram_link_code = None
    await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/notify")
async def toggle_notify(
    notify_activities: str = Form(""),
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    db_user = await session.get(User, user.id)
    db_user.notify_activities = notify_activities == "on"
    await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/users")
async def create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("manager"),
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    exists = await session.scalar(
        select(User).where(func.lower(User.email) == email.strip().lower())
    )
    if exists is None:
        session.add(
            User(
                name=name.strip(),
                email=email.strip().lower(),
                role=role if role in ("admin", "manager", "viewer") else "manager",
                password_hash=hash_password(password),
            )
        )
        await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    if user_id != user.id:  # don't delete yourself
        target = await session.get(User, user_id)
        if target is not None:
            await session.delete(target)
            await session.commit()
    return RedirectResponse(url="/settings", status_code=303)
