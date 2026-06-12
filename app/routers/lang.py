from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.i18n import normalize_lang
from app.models import User
from app.security import get_optional_user

router = APIRouter()


@router.get("/set-language")
async def set_language(
    request: Request,
    lang: str = "ru",
    next: str = "/",
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    lang = normalize_lang(lang)
    # Avoid open-redirects: only allow same-site relative paths.
    target = next if next.startswith("/") else "/"
    resp = RedirectResponse(url=target, status_code=303)
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    if user is not None:
        db_user = await session.get(User, user.id)
        db_user.language = lang
        await session.commit()
    return resp
