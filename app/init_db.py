"""Create tables (if missing) and seed the admin user.

Run as: python -m app.init_db

We use metadata.create_all for now so the app boots cleanly everywhere.
Alembic is wired up (see alembic/) for real migrations once the schema
stabilizes; switch the entrypoint to `alembic upgrade head` at that point.
"""

import asyncio

from sqlalchemy import select

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import User  # noqa: F401  (ensures models are registered)
from app.security import hash_password


async def init() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        existing = await session.scalar(select(User).limit(1))
        if existing is None:
            admin = User(
                email=settings.admin_email,
                name=settings.admin_name,
                role="admin",
                password_hash=hash_password(settings.admin_password),
            )
            session.add(admin)
            await session.commit()
            print(f"[init_db] Seeded admin user: {settings.admin_email}")
        else:
            print("[init_db] Users already exist; skipping seed.")

    print("[init_db] Database ready.")


if __name__ == "__main__":
    asyncio.run(init())
