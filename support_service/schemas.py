from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from support_service.models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=5, max_length=5000)
    order_id: Optional[int] = Field(None, description="Murojaat aniq buyurtmaga tegishli bo'lsa")
    priority: TicketPriority = TicketPriority.NORMAL


class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_user_id: Optional[int] = None
    author_role: Optional[str] = None
    is_system: bool
    body: str
    created_at: datetime


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_role: Optional[str] = None
    order_id: Optional[int] = None
    subject: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketListItem):
    body: str
    messages: list[MessageResponse] = []
