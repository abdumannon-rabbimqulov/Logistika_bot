"""Yordam (Support) xizmati endpointlari.

Kirish qoidalari:

    - murojaat yaratish — har qanday autentifikatsiyalangan foydalanuvchi
    - o'z murojaatini ko'rish/javob yozish — muallif
    - HAMMA murojaatni ko'rish, holatni o'zgartirish — xodim (admin yoki menejer)

Menejer bu yerda ham hech qanday moliyaviy ma'lumot ko'rmaydi: bu bazada narx,
balans yoki komissiya umuman saqlanmaydi (`support_service/models.py`).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from support_service import crud, queue, schemas
from support_service.auth import Principal, get_principal, require_staff
from support_service.db import get_db
from support_service.models import CLOSED_STATUSES, SupportTicket, TicketStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Yordam xizmati"])


async def _get_ticket_for(
    db: AsyncSession, ticket_id: int, principal: Principal
) -> SupportTicket:
    """Murojaatni topadi va faqat muallif yoki xodim ko'ra olishini tekshiradi.

    Topilmagan va begona murojaat uchun bir xil 404 qaytariladi: 403 qaytarilsa,
    begona odam ID larni sinab ko'rib qaysi murojaat mavjudligini aniqlab olardi.
    """
    ticket = await crud.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Murojaat topilmadi")
    if not principal.is_staff and ticket.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Murojaat topilmadi")
    return ticket


@router.post(
    "/tickets",
    response_model=schemas.TicketDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi murojaat yaratish",
)
async def create_ticket(
    data: schemas.TicketCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    ticket = await crud.create_ticket(
        db, data, user_id=principal.user_id, user_role=principal.role
    )

    # Hodisa: asosiy tizimdagi `workers/events_worker.py` buni olib adminlarga
    # Telegram xabari yuboradi. Support xizmati Telegram haqida hech narsa bilmaydi.
    await queue.publish_event(
        queue.EVENT_SUPPORT_TICKET_CREATED,
        {
            "ticket_id": ticket.id,
            "user_id": ticket.user_id,
            "user_role": ticket.user_role,
            "order_id": ticket.order_id,
            "subject": ticket.subject,
            "body": ticket.body,
            "priority": ticket.priority.value,
        },
    )
    return ticket


@router.get(
    "/tickets",
    response_model=List[schemas.TicketListItem],
    summary="Murojaatlar ro'yxati (o'ziniki; xodim uchun — hammasi)",
)
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
    ticket_status: Optional[TicketStatus] = Query(None, alias="status"),
    order_id: Optional[int] = Query(None),
    mine: bool = Query(False, description="Xodim uchun: faqat o'z murojaatlarim"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # Oddiy foydalanuvchi uchun filtr majburiy — `mine` bayrog'idan qat'i nazar
    # faqat o'z murojaatlarini ko'radi.
    user_filter = principal.user_id if (mine or not principal.is_staff) else None
    return await crud.list_tickets(
        db,
        user_id=user_filter,
        status=ticket_status,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=schemas.TicketDetail,
    summary="Murojaat tafsiloti (yozishmalar bilan)",
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    return await _get_ticket_for(db, ticket_id, principal)


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Murojaatga javob yozish",
)
async def add_message(
    ticket_id: int,
    data: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    ticket = await _get_ticket_for(db, ticket_id, principal)
    if ticket.status in CLOSED_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Murojaat yopilgan — yangi xabar yozib bo'lmaydi. Yangi murojaat oching.",
        )

    message = await crud.add_message(
        db,
        ticket,
        data.body,
        author_user_id=principal.user_id,
        author_role=principal.role,
    )

    await queue.publish_event(
        queue.EVENT_SUPPORT_TICKET_REPLIED,
        {
            "ticket_id": ticket.id,
            "message_id": message.id,
            "author_user_id": message.author_user_id,
            "author_role": message.author_role,
            "message": message.body,
            "order_id": ticket.order_id,
        },
    )
    return message


@router.patch(
    "/tickets/{ticket_id}/status",
    response_model=schemas.TicketDetail,
    summary="Murojaat holatini o'zgartirish (faqat xodim)",
)
async def update_status(
    ticket_id: int,
    data: schemas.TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_staff),
):
    ticket = await _get_ticket_for(db, ticket_id, principal)
    return await crud.set_status(db, ticket, data.status)
