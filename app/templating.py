from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import models
from app.config import settings
from app.i18n import LANGUAGE_NAMES, LANGUAGES, normalize_lang
from app.i18n import t as translate
from app.timeutil import LOCAL_TZ, UTC, to_local_input

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def fmt_dt(value: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(LOCAL_TZ).strftime(fmt)


templates.env.filters["dt"] = fmt_dt
templates.env.filters["dtinput"] = to_local_input

# Expose choice lists and settings to every template.
templates.env.globals.update(
    {
        "DEAL_STAGES": models.DEAL_STAGES,
        "ACCOUNT_TYPES": models.ACCOUNT_TYPES,
        "ACTIVITY_TYPES": models.ACTIVITY_TYPES,
        "TASK_STATUSES": models.TASK_STATUSES,
        "ROLES": models.ROLES,
        "BASE_URL": settings.base_url,
        "LINEAR_ENABLED": settings.linear_enabled,
        "TELEGRAM_ENABLED": settings.telegram_enabled,
        "LANGUAGES": LANGUAGES,
        "LANGUAGE_NAMES": LANGUAGE_NAMES,
        "CURRENCY": settings.currency_symbol,
    }
)


def resolve_lang(request: Request, user=None) -> str:
    """Logged-in users use their saved language; anonymous use the cookie."""
    if user is not None and getattr(user, "language", None):
        return normalize_lang(user.language)
    return normalize_lang(request.cookies.get("lang"))


def render(
    request: Request, name: str, user=None, status_code: int = 200, **ctx
) -> HTMLResponse:
    lang = resolve_lang(request, user)
    ctx.update(
        {
            "request": request,
            "current_user": user,
            "lang": lang,
            "t": lambda key, **kw: translate(lang, key, **kw),
        }
    )
    return templates.TemplateResponse(name, ctx, status_code=status_code)
