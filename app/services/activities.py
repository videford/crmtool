from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity


def log_activity(
    session: AsyncSession,
    *,
    account_id: int,
    type: str = "note",
    body: str | None = None,
    author_id: int | None = None,
    payload: dict | None = None,
) -> Activity:
    """Add an activity to the session. Caller is responsible for commit."""
    activity = Activity(
        account_id=account_id,
        type=type,
        body=body,
        author_id=author_id,
        payload=payload,
    )
    session.add(activity)
    return activity
