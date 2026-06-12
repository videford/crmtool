from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import (
    accounts,
    auth,
    contacts,
    dashboard,
    deals,
    lang,
    linear_webhook,
    meetings,
    settings_routes,
    tasks,
)
from app.security import NotAuthenticated, NotAuthorized
from app.templating import render

app = FastAPI(title="crmTool")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)


@app.exception_handler(NotAuthenticated)
async def _not_authenticated(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(NotAuthorized)
async def _not_authorized(request: Request, exc: NotAuthorized):
    return render(request, "403.html", status_code=403)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(lang.router)
app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(contacts.router)
app.include_router(deals.router)
app.include_router(meetings.router)
app.include_router(tasks.router)
app.include_router(settings_routes.router)
app.include_router(linear_webhook.router)
