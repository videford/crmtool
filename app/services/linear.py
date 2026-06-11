"""Linear GraphQL integration.

Tasks created in the CRM are mirrored as Linear issues. The inbound webhook
(see app/routers/linear_webhook.py) syncs status changes back into the CRM.
If Linear is not configured the helpers degrade gracefully: a local Task row
is still created, just without a linked issue.
"""

from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Task

LINEAR_API = "https://api.linear.app/graphql"

_ISSUE_CREATE = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier url }
  }
}
"""


async def _graphql(query: str, variables: dict) -> dict:
    headers = {
        "Authorization": settings.linear_api_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            LINEAR_API,
            json={"query": query, "variables": variables},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"Linear API error: {data['errors']}")
    return data["data"]


async def create_issue(title: str, description: str | None) -> dict | None:
    """Create a Linear issue. Returns {id, identifier, url} or None if disabled."""
    if not settings.linear_enabled:
        return None
    data = await _graphql(
        _ISSUE_CREATE,
        {
            "input": {
                "teamId": settings.linear_team_id,
                "title": title,
                "description": description or "",
            }
        },
    )
    result = data["issueCreate"]
    if not result.get("success"):
        raise RuntimeError("Linear issueCreate returned success=false")
    return result["issue"]


async def create_task_with_linear(
    session: AsyncSession,
    *,
    account_id: int,
    title: str,
    description: str | None = None,
    deal_id: int | None = None,
    source: str = "manual",
    account_name: str | None = None,
    assignee_id: int | None = None,
    due_date=None,
) -> Task:
    """Create a local Task and mirror it to Linear when configured."""
    task = Task(
        account_id=account_id,
        deal_id=deal_id,
        title=title,
        description=description,
        source=source,
        assignee_id=assignee_id,
        due_date=due_date,
    )

    if settings.linear_enabled:
        body = description or ""
        link = f"{settings.base_url}/accounts/{account_id}"
        ctx = f"\n\n---\nCRM: {account_name or 'account'} — {link}"
        try:
            issue = await create_issue(title, body + ctx)
            if issue:
                task.linear_issue_id = issue["id"]
                task.linear_url = issue["url"]
                task.synced_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001 — don't lose the local task
            task.description = (task.description or "") + (
                f"\n\n[Linear sync failed: {exc}]"
            )

    session.add(task)
    return task
