"""Create tables (if missing) and sync the admin user from env.

Run as: python -m app.init_db

We use metadata.create_all for now so the app boots cleanly everywhere.
Alembic is wired up (see alembic/) for real migrations once the schema
stabilizes; switch the entrypoint to `alembic upgrade head` at that point.
"""

import asyncio

from sqlalchemy import func, select, text

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import User  # noqa: F401  (ensures models are registered)
from app.security import hash_password

# Lightweight additive migrations for existing databases. create_all only
# creates missing tables, not new columns, so additive schema changes are
# applied here with ADD COLUMN IF NOT EXISTS (no-op on fresh installs).
_COLUMN_PATCHES = [
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assignee_id INTEGER REFERENCES users(id)",
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(8) DEFAULT 'ru'",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS address VARCHAR(512)",
]

# One-time data migrations to the guest/member/admin role model. Idempotent:
# after the first run no rows match the old role names.
_DATA_PATCHES = [
    "UPDATE users SET role='admin' WHERE role='manager'",
    "UPDATE users SET role='member' WHERE role='viewer'",
]


async def ensure_columns() -> None:
    """Apply additive column + data patches. Safe to run from any service."""
    async with engine.begin() as conn:
        for stmt in _COLUMN_PATCHES + _DATA_PATCHES:
            await conn.execute(text(stmt))


async def init() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _COLUMN_PATCHES + _DATA_PATCHES:
            await conn.execute(text(stmt))

    # Sync the seed admin from env on every boot. Env is the source of truth
    # for this account, so changing ADMIN_EMAIL/ADMIN_PASSWORD and redeploying
    # always lets you log in (values are stripped to avoid stray whitespace).
    email = settings.admin_email.strip().lower()
    name = settings.admin_name.strip()
    password = settings.admin_password.strip()

    async with SessionLocal() as session:
        admin = await session.scalar(
            select(User).where(func.lower(User.email) == email)
        )
        if admin is None:
            admin = User(email=email, name=name, role="admin")
            session.add(admin)
            action = "Seeded"
        else:
            action = "Updated"
        admin.name = name
        admin.role = "admin"
        admin.is_active = True
        admin.password_hash = hash_password(password)
        await session.commit()
        print(f"[init_db] {action} admin user: {email}")

    print("[init_db] Database ready.")


if __name__ == "__main__":
    asyncio.run(init())
