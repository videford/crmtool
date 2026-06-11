from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import DEAL_STAGES, Deal, User
from app.security import require_login, require_role
from app.services.activities import log_activity
from app.services.linear import create_task_with_linear
from app.templating import render

router = APIRouter(prefix="/deals")

# Stages that automatically spin up a Linear task when a deal enters them.
AUTO_TASK_STAGES = {
    "pilot": "Подготовить пилот/POC",
    "contract": "Подготовить договор и согласование",
}


@router.get("")
async def deal_board(
    request: Request,
    user: User = Depends(require_login),
    session: AsyncSession = Depends(get_session),
):
    deals = (
        await session.scalars(
            select(Deal)
            .options(selectinload(Deal.account))
            .order_by(Deal.created_at.desc())
        )
    ).all()
    columns = {stage: [] for stage in DEAL_STAGES}
    for deal in deals:
        columns.setdefault(deal.stage, []).append(deal)
    return render(request, "deals/board.html", user=user, columns=columns)


@router.post("/{deal_id}/stage")
async def change_stage(
    deal_id: int,
    stage: str = Form(...),
    redirect: str = Form(""),
    user: User = Depends(require_role("manager")),
    session: AsyncSession = Depends(get_session),
):
    deal = await session.get(
        Deal, deal_id, options=[selectinload(Deal.account)]
    )
    if deal is None:
        return RedirectResponse(url="/deals", status_code=303)
    if stage not in DEAL_STAGES:
        stage = deal.stage

    old_stage = deal.stage
    deal.stage = stage

    if stage != old_stage:
        log_activity(
            session,
            account_id=deal.account_id,
            type="stage_change",
            body=f"Сделка «{deal.title}»: {old_stage} → {stage}",
            author_id=user.id,
        )
        # Auto-create a Linear task on key stages.
        if stage in AUTO_TASK_STAGES:
            title = f"{AUTO_TASK_STAGES[stage]} — {deal.account.name}"
            await create_task_with_linear(
                session,
                account_id=deal.account_id,
                title=title,
                description=f"Авто-задача по сделке «{deal.title}» (этап {stage}).",
                deal_id=deal.id,
                source="auto",
                account_name=deal.account.name,
            )

    await session.commit()
    target = redirect or f"/accounts/{deal.account_id}#deals"
    return RedirectResponse(url=target, status_code=303)


@router.post("/{deal_id}/delete")
async def delete_deal(
    deal_id: int,
    user: User = Depends(require_role("manager")),
    session: AsyncSession = Depends(get_session),
):
    deal = await session.get(Deal, deal_id)
    account_id = deal.account_id if deal else None
    if deal is not None:
        await session.delete(deal)
        await session.commit()
    target = f"/accounts/{account_id}#deals" if account_id else "/deals"
    return RedirectResponse(url=target, status_code=303)
