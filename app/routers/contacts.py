from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Contact, User
from app.security import require_admin
from app.templating import render

router = APIRouter(prefix="/contacts")


@router.get("/{contact_id}/edit")
async def edit_contact_form(
    request: Request,
    contact_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    if contact is None:
        return render(request, "404.html", user=user, status_code=404)
    return render(request, "contacts/form.html", user=user, contact=contact)


@router.post("/{contact_id}/edit")
async def edit_contact(
    request: Request,
    contact_id: int,
    name: str = Form(...),
    position: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    telegram: str = Form(""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    if contact is None:
        return render(request, "404.html", user=user, status_code=404)
    contact.name = name.strip()
    contact.position = position.strip() or None
    contact.email = email.strip() or None
    contact.phone = phone.strip() or None
    contact.telegram = telegram.strip() or None
    await session.commit()
    return RedirectResponse(
        url=f"/accounts/{contact.account_id}#contacts", status_code=303
    )


@router.post("/{contact_id}/delete")
async def delete_contact(
    contact_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    account_id = contact.account_id if contact else None
    if contact is not None:
        await session.delete(contact)
        await session.commit()
    target = f"/accounts/{account_id}#contacts" if account_id else "/accounts"
    return RedirectResponse(url=target, status_code=303)
