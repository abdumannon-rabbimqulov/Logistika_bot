from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from support_service.models import SupportMessage, SupportTicket, TicketStatus
from support_service.schemas import TicketCreate


async def create_ticket(
    db: AsyncSession,
    data: TicketCreate,
    *,
    user_id: int,
    user_role: Optional[str],
) -> SupportTicket:
    ticket = SupportTicket(
        user_id=user_id,
        user_role=user_role,
        order_id=data.order_id,
        subject=data.subject,
        body=data.body,
        priority=data.priority,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    await db.commit()
    # `messages` bo'sh bo'lsa ham eager-load qilinadi: async kontekstda lazy-load
    # `MissingGreenlet` bilan yiqiladi (asosiy loyihada ham shu tuzoqqa tushilgan).
    await db.refresh(ticket, attribute_names=["messages"])
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: int) -> Optional[SupportTicket]:
    result = await db.execute(
        select(SupportTicket)
        .options(selectinload(SupportTicket.messages))
        .where(SupportTicket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def list_tickets(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    status: Optional[TicketStatus] = None,
    order_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[SupportTicket]:
    """`user_id=None` — hamma murojaatlar (faqat xodimlar uchun, router tekshiradi)."""
    stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(SupportTicket.user_id == user_id)
    if status is not None:
        stmt = stmt.where(SupportTicket.status == status)
    if order_id is not None:
        stmt = stmt.where(SupportTicket.order_id == order_id)

    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    ticket: SupportTicket,
    body: str,
    *,
    author_user_id: Optional[int] = None,
    author_role: Optional[str] = None,
    is_system: bool = False,
) -> SupportMessage:
    message = SupportMessage(
        ticket_id=ticket.id,
        author_user_id=author_user_id,
        author_role=author_role,
        is_system=is_system,
        body=body,
    )
    db.add(message)

    # Xodim javob yozsa murojaat avtomatik "ishlanmoqda" ga o'tadi — operatorga
    # qo'lda holat o'zgartirishni eslatib turish shart bo'lmasin.
    if not is_system and author_role in {"admin", "manager"} and ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(message)
    return message


async def set_status(
    db: AsyncSession, ticket: SupportTicket, new_status: TicketStatus
) -> SupportTicket:
    ticket.status = new_status
    await db.commit()
    await db.refresh(ticket, attribute_names=["status", "updated_at"])
    return ticket


async def list_open_tickets_for_order(
    db: AsyncSession, order_id: int
) -> Sequence[SupportTicket]:
    """Buyurtma hodisasi kelganda tizim izohi qo'shiladigan murojaatlar.

    Yopilgan (`resolved`/`closed`) murojaatlar chetlab o'tiladi — yopilgan ishga
    yangi xabar qo'shish uni qayta ochilgandek ko'rsatardi.
    """
    result = await db.execute(
        select(SupportTicket).where(
            SupportTicket.order_id == order_id,
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
        )
    )
    return list(result.scalars().all())
