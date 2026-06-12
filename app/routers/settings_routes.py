from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import ROLES, User
from app.security import (
    hash_password,
    is_main_admin,
    new_link_code,
    require_admin,
    require_member,
)
from app.templating import render

router = APIRouter(prefix="/settings")


@router.get("")
async def settings_page(
    request: Request,
    user: User = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    db_user = await session.get(User, user.id)
    # Ensure a link code exists so the "Link Telegram" deep link works without
    # the user having to press anything first.
    tg_link = None
    if (
        settings.telegram_enabled
        and settings.telegram_bot_username
        and not db_user.telegram_chat_id
    ):
        if not db_user.telegram_link_code:
            db_user.telegram_link_code = new_link_code()
            await session.commit()
        tg_link = (
            f"https://t.me/{settings.telegram_bot_username}"
            f"?start={db_user.telegram_link_code}"
        )

    users = []
    if user.role == "admin":
        users = (await session.scalars(select(User).order_by(User.name))).all()
    return render(
        request,
        "settings.html",
        user=db_user,
        users=users,
        tg_link=tg_link,
        is_main_admin=is_main_admin,
    )


@router.post("/telegram/regenerate")
async def regenerate_link_code(
    user: User = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    db_user = await session.get(User, user.id)
    db_user.telegram_link_code = new_link_code()
    await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/telegram/unlink")
async def unlink_telegram(
    user: User = Depends(require_member),
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
    user: User = Depends(require_member),
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
    role: str = Form("member"),
    user: User = Depends(require_admin),
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
                role=role if role in ROLES else "member",
                password_hash=hash_password(password),
            )
        )
        await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/users/{user_id}/role")
async def set_user_role(
    user_id: int,
    role: str = Form(...),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    target = await session.get(User, user_id)
    if target is not None and role in ROLES and not is_main_admin(target):
        target.role = role
        await session.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    target = await session.get(User, user_id)
    # Never delete yourself or the protected main admin.
    if target is not None and target.id != user.id and not is_main_admin(target):
        await session.delete(target)
        await session.commit()
    return RedirectResponse(url="/settings", status_code=303)
