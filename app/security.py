import secrets

import bcrypt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import User


class NotAuthenticated(Exception):
    """Raised when a login-required route has no authenticated user."""


class NotAuthorized(Exception):
    """Raised when an authenticated user lacks the required role."""


class PendingApproval(Exception):
    """Raised when a logged-in guest awaits admin approval."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def new_link_code() -> str:
    return secrets.token_hex(4)


def is_main_admin(user: User) -> bool:
    """The seeded admin (ADMIN_EMAIL) is protected: never demoted or deleted."""
    return user.email.strip().lower() == settings.admin_email.strip().lower()


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = await session.get(User, user_id)
    if user and user.is_active:
        return user
    return None


async def require_login(
    user: User | None = Depends(get_optional_user),
) -> User:
    """Any authenticated, active user (including a pending guest)."""
    if user is None:
        raise NotAuthenticated()
    return user


async def require_member(
    user: User | None = Depends(get_optional_user),
) -> User:
    """Member or admin. Guests are bounced to the pending page."""
    if user is None:
        raise NotAuthenticated()
    if user.role == "guest":
        raise PendingApproval()
    return user


async def require_admin(
    user: User | None = Depends(get_optional_user),
) -> User:
    if user is None:
        raise NotAuthenticated()
    if user.role == "guest":
        raise PendingApproval()
    if user.role != "admin":
        raise NotAuthorized()
    return user
