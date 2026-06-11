"""Inbound Linear webhook: sync issue status changes back into CRM tasks.

Configure in Linear: Settings → API → Webhooks → URL = {BASE_URL}/linear/webhook,
with the "Issues" resource enabled and a signing secret = LINEAR_WEBHOOK_SECRET.
"""

import hashlib
import hmac

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Task

router = APIRouter(prefix="/linear")

# Linear issue state.type -> CRM task status
STATE_MAP = {
    "completed": "done",
    "canceled": "canceled",
    "started": "in_progress",
    "unstarted": "open",
    "backlog": "open",
    "triage": "open",
}


def _verify(body: bytes, signature: str | None) -> bool:
    if not settings.linear_webhook_secret:
        return True  # no secret configured -> accept (dev)
    if not signature:
        return False
    digest = hmac.new(
        settings.linear_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/webhook")
async def linear_webhook(request: Request):
    body = await request.body()
    if not _verify(body, request.headers.get("Linear-Signature")):
        return {"ok": False, "reason": "bad signature"}

    payload = await request.json()
    data = payload.get("data") or {}
    issue_id = data.get("id")
    if not issue_id:
        return {"ok": True, "skipped": "no issue id"}

    state = (data.get("state") or {}).get("type")
    new_status = STATE_MAP.get(state)

    async with SessionLocal() as session:
        task = await session.scalar(
            select(Task).where(Task.linear_issue_id == issue_id)
        )
        if task and new_status and task.status != new_status:
            task.status = new_status
            await session.commit()

    return {"ok": True}
