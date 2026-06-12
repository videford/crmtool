from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.i18n import normalize_lang
from app.i18n import t as translate
from app.models import User
from app.security import hash_password, verify_password
from app.templating import render, resolve_lang

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    return render(request, "login.html", allow_registration=settings.allow_registration)


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    user = await session.scalar(
        select(User).where(func.lower(User.email) == email.strip().lower())
    )
    if user is None or not user.is_active or not verify_password(
        password, user.password_hash
    ):
        return render(
            request,
            "login.html",
            error=translate(resolve_lang(request), "auth.error"),
            allow_registration=settings.allow_registration,
            status_code=401,
        )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/register")
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    if not settings.allow_registration:
        return render(
            request,
            "login.html",
            error=translate(resolve_lang(request), "auth.reg_disabled"),
            allow_registration=False,
            status_code=403,
        )
    return render(request, "register.html")


@router.post("/register")
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    lang = resolve_lang(request)
    if not settings.allow_registration:
        return render(
            request, "login.html", error=translate(lang, "auth.reg_disabled"),
            allow_registration=False, status_code=403,
        )
    email_norm = email.strip().lower()
    exists = await session.scalar(
        select(User).where(func.lower(User.email) == email_norm)
    )
    if exists is not None:
        return render(
            request,
            "register.html",
            error=translate(lang, "auth.email_taken"),
            status_code=409,
        )
    role = settings.default_role if settings.default_role in (
        "admin", "manager", "viewer"
    ) else "manager"
    user = User(
        name=name.strip(),
        email=email_norm,
        role=role,
        language=normalize_lang(request.cookies.get("lang")),
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.commit()
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
