"""Logistika AI Agent — Gemini-asosida role-aware toolkit.

- `build_system_instruction(role, language)` — base + role + til.
- `TOOL_DEFINITIONS` — har bir tool'ga `roles` ro'yxati.
- `LogistikaAgent` joriy modelni `ai.settings.get_current_model()` orqali oladi
  va sinxron Gemini chaqiruvlarini `asyncio.to_thread` ichida bajaradi.
- `LogistikaToolkit` mavjud `crud` modullariga delegatsiya qiladi va ownership tekshiradi.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import (
    AVAILABLE_AI_MODELS,
    LANG_DIRECTIVE,
    ROLE_INSTRUCTIONS,
    SYSTEM_INSTRUCTION_BASE,
    async_session,
    client,
)
from order import crud as order_crud, schemas as order_schemas
from order.models import Order, OrderOffer, OrderStatus, OfferStatus
from driver import crud as driver_crud, schemas as driver_schemas
from driver.models import (
    Driver,
    DriverAnnouncement,
    AnnouncementOffer,
    AnnouncementOfferStatus,
)
from users import crud as user_crud
from users.models import User, UserRole
from users.schemas import UserUpdate
from ai.settings import get_current_model, set_current_model
from ai.limits import set_user_limit as set_user_limit_setting
from ai.models import AIUsage

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# SYSTEM INSTRUCTION BUILDER
# ════════════════════════════════════════════════════════════


def build_system_instruction(role: str, language: str) -> str:
    """Roleingiz va tilingizni o'rnatuvchi system instruction qaytaradi."""
    role_part = ROLE_INSTRUCTIONS.get(role, ROLE_INSTRUCTIONS["guest"])
    lang_part = LANG_DIRECTIVE.get(language, LANG_DIRECTIVE["uz"])
    return f"{SYSTEM_INSTRUCTION_BASE.strip()}\n\n{role_part}\n\n{lang_part}"


# ════════════════════════════════════════════════════════════
# TOOL DECLARATIONS (Gemini function-calling schema)
# ════════════════════════════════════════════════════════════


def _decl(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if parameters is None:
        parameters = {"type": "object", "properties": {}}
    return {"name": name, "description": description, "parameters": parameters}


TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    # ── Common ─────────────────────────────────────────────
    {
        "method": "get_my_profile",
        "roles": ["sender", "driver", "admin", "guest"],
        "declaration": _decl(
            "get_my_profile",
            "Foydalanuvchining (o'zining) profil ma'lumotlarini qaytaradi.",
        ),
    },
    {
        "method": "update_my_profile",
        "roles": ["sender", "driver", "admin"],
        "declaration": _decl(
            "update_my_profile",
            "Foydalanuvchining ismi/bio/tilini yangilaydi.",
            {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "bio": {"type": "string"},
                    "language": {"type": "string", "description": "uz | uz_cyrl | ru"},
                    "phone_number": {"type": "string"},
                },
            },
        ),
    },
    {
        "method": "list_truck_types",
        "roles": ["sender", "driver", "admin"],
        "declaration": _decl(
            "list_truck_types",
            "Barcha mavjud yuk mashinasi turlari va ID larini qaytaradi.",
        ),
    },
    {
        "method": "get_order",
        "roles": ["sender", "driver", "admin"],
        "declaration": _decl(
            "get_order",
            "Bitta buyurtma haqida ma'lumot olish.",
            {
                "type": "object",
                "properties": {"order_id": {"type": "integer"}},
                "required": ["order_id"],
            },
        ),
    },
    # ── Sender ─────────────────────────────────────────────
    {
        "method": "create_order",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "create_order",
            "Yangi yuk buyurtmasini yaratadi (Toshkent->Andijon kabi).",
            {
                "type": "object",
                "properties": {
                    "cargo_name": {"type": "string"},
                    "weight": {"type": "number", "description": "tonna"},
                    "from_address": {"type": "string"},
                    "to_address": {"type": "string"},
                    "price": {"type": "number"},
                    "required_truck_type_id": {"type": "integer"},
                },
                "required": [
                    "cargo_name",
                    "weight",
                    "from_address",
                    "to_address",
                    "price",
                    "required_truck_type_id",
                ],
            },
        ),
    },
    {
        "method": "list_my_orders",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "list_my_orders",
            "Foydalanuvchining buyurtmalari ro'yxati.",
            {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "pending|accepted|in_progress|completed|cancelled",
                    }
                },
            },
        ),
    },
    {
        "method": "cancel_order",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "cancel_order",
            "O'z buyurtmasini bekor qilish (status=CANCELLED).",
            {
                "type": "object",
                "properties": {"order_id": {"type": "integer"}},
                "required": ["order_id"],
            },
        ),
    },
    {
        "method": "list_offers_for_my_order",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "list_offers_for_my_order",
            "Mening buyurtmamga kelgan haydovchi takliflari.",
            {
                "type": "object",
                "properties": {"order_id": {"type": "integer"}},
                "required": ["order_id"],
            },
        ),
    },
    {
        "method": "accept_offer",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "accept_offer",
            "Buyurtmaga kelgan taklifni qabul qilish (haydovchi belgilanadi, qolganlari OUTBID).",
            {
                "type": "object",
                "properties": {"offer_id": {"type": "integer"}},
                "required": ["offer_id"],
            },
        ),
    },
    {
        "method": "reject_offer",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "reject_offer",
            "Taklifni rad etish (sabab ixtiyoriy).",
            {
                "type": "object",
                "properties": {
                    "offer_id": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["offer_id"],
            },
        ),
    },
    {
        "method": "find_announcements",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "find_announcements",
            "Haydovchilarning aktiv safar e'lonlarini topish.",
            {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        ),
    },
    {
        "method": "make_offer_on_announcement",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "make_offer_on_announcement",
            "Haydovchi e'loniga yuk taklif yuborish.",
            {
                "type": "object",
                "properties": {
                    "announcement_id": {"type": "integer"},
                    "cargo_name": {"type": "string"},
                    "offered_price": {"type": "number"},
                    "cargo_weight": {"type": "number"},
                    "comment": {"type": "string"},
                },
                "required": ["announcement_id", "cargo_name", "offered_price"],
            },
        ),
    },
    {
        "method": "rate_driver",
        "roles": ["sender", "admin"],
        "declaration": _decl(
            "rate_driver",
            "Yakunlangan buyurtma uchun haydovchini baholash (1..5).",
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "score": {"type": "integer"},
                    "comment": {"type": "string"},
                },
                "required": ["order_id", "score"],
            },
        ),
    },
    # ── Driver ─────────────────────────────────────────────
    {
        "method": "find_orders",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "find_orders",
            "Yangi (PENDING) yuk buyurtmalarini topib qaytarish.",
            {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                    "max_weight_ton": {"type": "number"},
                    "limit": {"type": "integer"},
                },
            },
        ),
    },
    {
        "method": "make_offer_on_order",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "make_offer_on_order",
            "Mavjud buyurtmaga taklif (narx) yuborish.",
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "offered_price": {"type": "number"},
                    "comment": {"type": "string"},
                },
                "required": ["order_id", "offered_price"],
            },
        ),
    },
    {
        "method": "create_announcement",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "create_announcement",
            "Yangi safar e'loni yaratish (origin->destination, narx, sana).",
            {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                    "price": {"type": "number"},
                    "departure_date_iso": {
                        "type": "string",
                        "description": "ISO-8601 format (2025-05-10T08:00:00Z)",
                    },
                    "available_weight": {"type": "number"},
                    "description": {"type": "string"},
                },
                "required": ["from_city", "to_city", "price", "departure_date_iso"],
            },
        ),
    },
    {
        "method": "list_my_announcements",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "list_my_announcements",
            "Mening barcha safar e'lonlarim.",
        ),
    },
    {
        "method": "list_offers_on_my_announcement",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "list_offers_on_my_announcement",
            "Mening e'lonimga kelgan mijoz takliflari.",
            {
                "type": "object",
                "properties": {"announcement_id": {"type": "integer"}},
                "required": ["announcement_id"],
            },
        ),
    },
    {
        "method": "accept_announcement_offer",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "accept_announcement_offer",
            "E'lonimga kelgan mijoz taklifini qabul qilish.",
            {
                "type": "object",
                "properties": {"offer_id": {"type": "integer"}},
                "required": ["offer_id"],
            },
        ),
    },
    {
        "method": "reject_announcement_offer",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "reject_announcement_offer",
            "E'lonimga kelgan mijoz taklifini rad etish.",
            {
                "type": "object",
                "properties": {
                    "offer_id": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["offer_id"],
            },
        ),
    },
    {
        "method": "update_my_driver_profile",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "update_my_driver_profile",
            "Haydovchi profil ma'lumotlarini yangilash (joylashuv shahar, mavjudlik).",
            {
                "type": "object",
                "properties": {
                    "current_city": {"type": "string"},
                    "current_region": {"type": "string"},
                    "is_available": {"type": "boolean"},
                },
            },
        ),
    },
    {
        "method": "update_gps",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "update_gps",
            "Joriy GPS koordinatalarini yangilash.",
            {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
            },
        ),
    },
    {
        "method": "rate_user",
        "roles": ["driver", "admin"],
        "declaration": _decl(
            "rate_user",
            "Yakunlangan buyurtma uchun mijozni baholash.",
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "score": {"type": "integer"},
                    "comment": {"type": "string"},
                },
                "required": ["order_id", "score"],
            },
        ),
    },
    # ── Admin ──────────────────────────────────────────────
    {
        "method": "get_ai_usage_stats",
        "roles": ["admin"],
        "declaration": _decl(
            "get_ai_usage_stats",
            "Bugungi (yoki ko'rsatilgan kun) AI sarflari statistikasi.",
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "date_iso": {"type": "string", "description": "YYYY-MM-DD"},
                },
            },
        ),
    },
    {
        "method": "set_ai_model",
        "roles": ["admin"],
        "declaration": _decl(
            "set_ai_model",
            "Joriy AI model nomini almashtirish (admin).",
            {
                "type": "object",
                "properties": {"model_name": {"type": "string"}},
                "required": ["model_name"],
            },
        ),
    },
    {
        "method": "list_available_models",
        "roles": ["admin"],
        "declaration": _decl(
            "list_available_models",
            "Tanlash mumkin bo'lgan model'lar ro'yxati.",
        ),
    },
    {
        "method": "set_user_limit",
        "roles": ["admin"],
        "declaration": _decl(
            "set_user_limit",
            "Bir foydalanuvchi uchun kunlik AI so'rov limiti.",
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "daily_requests": {"type": "integer"},
                },
                "required": ["user_id", "daily_requests"],
            },
        ),
    },
]


_TOOL_BY_NAME: Dict[str, Dict[str, Any]] = {t["declaration"]["name"]: t for t in TOOL_DEFINITIONS}


def get_tools_for_role(role: str) -> List[Dict[str, Any]]:
    """Role'ga ruxsat etilgan tool deklaratsiyalarini qaytaradi."""
    return [t["declaration"] for t in TOOL_DEFINITIONS if role in t["roles"]]


def _is_tool_allowed(tool_name: str, role: str) -> bool:
    tool = _TOOL_BY_NAME.get(tool_name)
    return bool(tool and role in tool["roles"])


# ════════════════════════════════════════════════════════════
# TOOLKIT — har bir method mavjud crud'larga delegatsiya qiladi.
# ════════════════════════════════════════════════════════════


class LogistikaToolkit:
    """AI Agent uchun amaliy funksiyalar (Gemini'ning function-calling natijasi shu yerda bajariladi)."""

    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.user_id = user.id
        self.role = user.role.value if user.role else "guest"

    # ── Common ──────────────────────────────────────────

    async def get_my_profile(self) -> str:
        u = self.user
        return (
            f"Profil: id={u.id}, ism={u.full_name}, role={self.role}, "
            f"til={u.language}, telefon={u.phone_number or '—'}"
        )

    async def update_my_profile(
        self,
        full_name: Optional[str] = None,
        bio: Optional[str] = None,
        language: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> str:
        update = UserUpdate(
            full_name=full_name,
            bio=bio,
            language=language,
            phone_number=phone_number,
        )
        await user_crud.update_user(self.db, self.user, update)
        return "Profil yangilandi."

    async def list_truck_types(self) -> str:
        types = await driver_crud.get_all_truck_types(self.db)
        if not types:
            return "Hozircha mashina turlari bazada yo'q."
        return "Mavjud yuk mashinalari:\n" + "\n".join(
            f"- ID {t.id}: {t.name} ({t.max_weight} tonnagacha, {t.max_volume} m³)"
            for t in types
        )

    async def get_order(self, order_id: int) -> str:
        o = await order_crud.get_order(self.db, order_id)
        if not o:
            return f"Buyurtma #{order_id} topilmadi."
        if self.role != "admin":
            d = await driver_crud.get_driver_by_user_id(self.db, self.user_id)
            owner = o.customer_id == self.user_id or (d and o.driver_id == d.id)
            if not owner:
                return "Bu buyurtmaga kirish ruxsatingiz yo'q."
        wp = ", ".join(
            f"{w.sequence}.{w.waypoint_type.value}({w.address or '—'})"
            for w in (o.waypoints or [])
        )
        return (
            f"Buyurtma #{o.id}: yuk={o.cargo_name}, vazn={o.weight}t, "
            f"narx={o.price} {o.currency}, status={o.status.value}, marshrut=[{wp}]"
        )

    # ── Sender ──────────────────────────────────────────

    async def create_order(
        self,
        cargo_name: str,
        weight: float,
        from_address: str,
        to_address: str,
        price: float,
        required_truck_type_id: int,
    ) -> str:
        try:
            order_data = order_schemas.OrderCreate(
                cargo_name=cargo_name,
                weight=weight,
                price=price,
                required_truck_type_id=required_truck_type_id,
                waypoints=[
                    order_schemas.OrderWaypointCreate(
                        sequence=1, waypoint_type="pickup", address=from_address
                    ),
                    order_schemas.OrderWaypointCreate(
                        sequence=2, waypoint_type="delivery", address=to_address
                    ),
                ],
            )
            order = await order_crud.create_order(
                self.db, order_data, customer_id=self.user_id
            )
            return f"Buyurtma #{order.id} yaratildi: {cargo_name}, {price} {order.currency}."
        except Exception as exc:
            logger.error("AI create_order error: %s", exc)
            return f"Buyurtma yaratishda xato: {exc}"

    async def list_my_orders(self, status: Optional[str] = None) -> str:
        orders = await order_crud.get_all_orders(
            self.db, customer_id=self.user_id, status=status
        )
        if not orders:
            return "Sizda hali buyurtmalar yo'q."
        return "Buyurtmalaringiz:\n" + "\n".join(
            f"- #{o.id} {o.cargo_name} ({o.status.value}, {o.price} {o.currency})"
            for o in orders
        )

    async def cancel_order(self, order_id: int) -> str:
        o = await order_crud.get_order(self.db, order_id)
        if not o:
            return f"Buyurtma #{order_id} topilmadi."
        if o.customer_id != self.user_id and self.role != "admin":
            return "Bu buyurtmani bekor qilish ruxsatingiz yo'q."
        if o.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            return f"Buyurtma allaqachon {o.status.value}."
        await order_crud.update_order(
            self.db, order_id, order_schemas.OrderUpdate(status=order_schemas.OrderStatus.CANCELLED)
        )
        return f"Buyurtma #{order_id} bekor qilindi."

    async def list_offers_for_my_order(self, order_id: int) -> str:
        o = await order_crud.get_order(self.db, order_id)
        if not o:
            return f"Buyurtma #{order_id} topilmadi."
        if o.customer_id != self.user_id and self.role != "admin":
            return "Ruxsat berilmagan."
        offers = await order_crud.get_order_offers(self.db, order_id)
        if not offers:
            return "Hozircha takliflar yo'q."
        return f"#{order_id} ga takliflar:\n" + "\n".join(
            f"- offer#{f.id} driver#{f.driver_id} narx={f.offered_price} {f.currency} status={f.status.value}"
            for f in offers
        )

    async def _accept_offer_atomic(self, offer_id: int) -> str:
        offer = await order_crud.get_order_offer(self.db, offer_id)
        if not offer:
            return f"Taklif #{offer_id} topilmadi."
        order = await order_crud.get_order(self.db, offer.order_id)
        if not order or (order.customer_id != self.user_id and self.role != "admin"):
            return "Ruxsat berilmagan."
        if offer.status not in (OfferStatus.PENDING, OfferStatus.SEEN):
            return f"Taklif allaqachon {offer.status.value}."

        offer.accept()
        order.driver_id = offer.driver_id
        order.status = OrderStatus.ACCEPTED

        result = await self.db.execute(
            select(OrderOffer).where(
                OrderOffer.order_id == order.id,
                OrderOffer.id != offer.id,
                OrderOffer.status.in_((OfferStatus.PENDING, OfferStatus.SEEN)),
            )
        )
        for other in result.scalars().all():
            other.status = OfferStatus.OUTBID

        await self.db.commit()
        return f"Taklif #{offer_id} qabul qilindi, buyurtma #{order.id} haydovchi #{offer.driver_id} ga berildi."

    async def accept_offer(self, offer_id: int) -> str:
        return await self._accept_offer_atomic(offer_id)

    async def reject_offer(self, offer_id: int, reason: Optional[str] = None) -> str:
        offer = await order_crud.get_order_offer(self.db, offer_id)
        if not offer:
            return f"Taklif #{offer_id} topilmadi."
        order = await order_crud.get_order(self.db, offer.order_id)
        if not order or (order.customer_id != self.user_id and self.role != "admin"):
            return "Ruxsat berilmagan."
        offer.reject(reason)
        await self.db.commit()
        return f"Taklif #{offer_id} rad etildi."

    async def find_announcements(
        self,
        from_city: Optional[str] = None,
        to_city: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        anns = await driver_crud.get_all_announcements(self.db)
        filtered = []
        for a in anns:
            if not a.is_active:
                continue
            wps = a.waypoints or []
            if from_city and not any(w.city.lower() == from_city.lower() for w in wps):
                continue
            if to_city and not any(w.city.lower() == to_city.lower() for w in wps):
                continue
            filtered.append(a)
        filtered = filtered[: max(1, min(limit or 10, 50))]
        if not filtered:
            return "Mos e'lonlar topilmadi."
        return "E'lonlar:\n" + "\n".join(
            f"- ann#{a.id} driver#{a.driver_id} {a.price} {a.currency} departure={a.departure_date}"
            for a in filtered
        )

    async def make_offer_on_announcement(
        self,
        announcement_id: int,
        cargo_name: str,
        offered_price: float,
        cargo_weight: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> str:
        ann = await driver_crud.get_announcement(self.db, announcement_id)
        if not ann:
            return f"E'lon #{announcement_id} topilmadi."
        offer_data = driver_schemas.AnnouncementOfferCreate(
            announcement_id=announcement_id,
            customer_id=self.user_id,
            cargo_name=cargo_name,
            offered_price=offered_price,
            cargo_weight=cargo_weight,
            comment=comment,
        )
        offer = await driver_crud.create_announcement_offer(self.db, offer_data)
        return f"Taklif #{offer.id} yuborildi, narx {offered_price}."

    async def rate_driver(self, order_id: int, score: int, comment: Optional[str] = None) -> str:
        from ai import crud as ai_crud
        from ai import schemas as ai_schemas
        if not (1 <= score <= 5):
            return "Baho 1 dan 5 gacha bo'lishi kerak."
        o = await order_crud.get_order(self.db, order_id)
        if not o:
            return f"Buyurtma #{order_id} topilmadi."
        if o.customer_id != self.user_id and self.role != "admin":
            return "Ruxsat berilmagan."
        if not o.driver_id:
            return "Bu buyurtmada haydovchi belgilanmagan."
        rating = await ai_crud.create_rating(
            self.db,
            ai_schemas.RatingCreate(
                order_id=order_id,
                target_type=ai_schemas.RatingTarget.DRIVER,
                target_driver=o.driver_id,
                score=score,
                comment=comment,
                rated_by_user=self.user_id,
            ),
        )
        return f"Baho #{rating.id} saqlandi ({score}/5)."

    # ── Driver ──────────────────────────────────────────

    async def _require_driver(self) -> Optional[Driver]:
        return await driver_crud.get_driver_by_user_id(self.db, self.user_id)

    async def find_orders(
        self,
        from_city: Optional[str] = None,
        to_city: Optional[str] = None,
        max_weight_ton: Optional[float] = None,
        limit: int = 10,
    ) -> str:
        orders = await order_crud.get_all_orders(self.db, status="pending")
        out = []
        for o in orders:
            if max_weight_ton is not None and float(o.weight) > float(max_weight_ton):
                continue
            wps = o.waypoints or []
            if from_city and not any(
                (w.address or "").lower().find(from_city.lower()) >= 0 for w in wps
            ):
                continue
            if to_city and not any(
                (w.address or "").lower().find(to_city.lower()) >= 0 for w in wps
            ):
                continue
            out.append(o)
        out = out[: max(1, min(limit or 10, 50))]
        if not out:
            return "Mos buyurtmalar topilmadi."
        return "Buyurtmalar:\n" + "\n".join(
            f"- order#{o.id} {o.cargo_name} {o.weight}t {o.price} {o.currency}"
            for o in out
        )

    async def make_offer_on_order(
        self, order_id: int, offered_price: float, comment: Optional[str] = None
    ) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Avval haydovchi profili to'ldirilishi kerak."
        offer_data = order_schemas.OrderOfferCreate(
            order_id=order_id,
            driver_id=driver.id,
            offered_price=offered_price,
            comment=comment,
        )
        offer = await order_crud.create_order_offer(self.db, offer_data)
        return f"Taklif #{offer.id} buyurtma #{order_id} ga yuborildi."

    async def create_announcement(
        self,
        from_city: str,
        to_city: str,
        price: float,
        departure_date_iso: str,
        available_weight: Optional[float] = None,
        description: Optional[str] = None,
    ) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Avval haydovchi profili to'ldirilishi kerak."
        try:
            departure = datetime.fromisoformat(departure_date_iso.replace("Z", "+00:00"))
        except ValueError:
            return "departure_date_iso noto'g'ri format. Misol: 2025-05-10T08:00:00Z"
        ann_data = driver_schemas.DriverAnnouncementCreate(
            driver_id=driver.id,
            price=price,
            available_weight=available_weight,
            departure_date=departure,
            description=description,
            waypoints=[
                driver_schemas.AnnouncementWaypointCreate(
                    sequence=1, waypoint_type="origin", city=from_city
                ),
                driver_schemas.AnnouncementWaypointCreate(
                    sequence=2, waypoint_type="destination", city=to_city
                ),
            ],
        )
        ann = await driver_crud.create_announcement(self.db, ann_data)
        return f"E'lon #{ann.id} yaratildi: {from_city} -> {to_city}, {price} so'm."

    async def list_my_announcements(self) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        anns = await driver_crud.get_all_announcements(self.db, driver_id=driver.id)
        if not anns:
            return "Sizda e'lonlar yo'q."
        return "E'lonlaringiz:\n" + "\n".join(
            f"- ann#{a.id} {a.price} {a.currency} status={a.status.value}"
            for a in anns
        )

    async def list_offers_on_my_announcement(self, announcement_id: int) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        ann = await driver_crud.get_announcement(self.db, announcement_id)
        if not ann or (ann.driver_id != driver.id and self.role != "admin"):
            return "Ruxsat berilmagan."
        offers = await driver_crud.get_announcement_offers(self.db, announcement_id)
        if not offers:
            return "Hozircha takliflar yo'q."
        return f"#{announcement_id} ga takliflar:\n" + "\n".join(
            f"- offer#{f.id} customer#{f.customer_id} {f.offered_price} {f.currency} status={f.status.value}"
            for f in offers
        )

    async def accept_announcement_offer(self, offer_id: int) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        offer = await driver_crud.get_announcement_offer(self.db, offer_id)
        if not offer:
            return f"Taklif #{offer_id} topilmadi."
        ann = await driver_crud.get_announcement(self.db, offer.announcement_id)
        if not ann or (ann.driver_id != driver.id and self.role != "admin"):
            return "Ruxsat berilmagan."
        offer.accept()
        await self.db.commit()
        return f"Taklif #{offer_id} qabul qilindi."

    async def reject_announcement_offer(
        self, offer_id: int, reason: Optional[str] = None
    ) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        offer = await driver_crud.get_announcement_offer(self.db, offer_id)
        if not offer:
            return f"Taklif #{offer_id} topilmadi."
        ann = await driver_crud.get_announcement(self.db, offer.announcement_id)
        if not ann or (ann.driver_id != driver.id and self.role != "admin"):
            return "Ruxsat berilmagan."
        offer.reject(reason)
        await self.db.commit()
        return f"Taklif #{offer_id} rad etildi."

    async def update_my_driver_profile(
        self,
        current_city: Optional[str] = None,
        current_region: Optional[str] = None,
        is_available: Optional[bool] = None,
    ) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        data = driver_schemas.DriverUpdate(
            current_city=current_city,
            current_region=current_region,
            is_available=is_available,
        )
        await driver_crud.update_driver(self.db, driver.id, data)
        return "Haydovchi profili yangilandi."

    async def update_gps(self, latitude: float, longitude: float) -> str:
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        driver.last_latitude = latitude
        driver.last_longitude = longitude
        driver.last_location_at = datetime.now(timezone.utc)
        driver.is_live_location_active = True
        await self.db.commit()
        return f"GPS yangilandi: ({latitude}, {longitude})."

    async def rate_user(self, order_id: int, score: int, comment: Optional[str] = None) -> str:
        from ai import crud as ai_crud
        from ai import schemas as ai_schemas
        if not (1 <= score <= 5):
            return "Baho 1 dan 5 gacha bo'lishi kerak."
        driver = await self._require_driver()
        if not driver:
            return "Haydovchi profili topilmadi."
        o = await order_crud.get_order(self.db, order_id)
        if not o:
            return f"Buyurtma #{order_id} topilmadi."
        if o.driver_id != driver.id and self.role != "admin":
            return "Ruxsat berilmagan."
        rating = await ai_crud.create_rating(
            self.db,
            ai_schemas.RatingCreate(
                order_id=order_id,
                target_type=ai_schemas.RatingTarget.USER,
                target_user=o.customer_id,
                score=score,
                comment=comment,
                rated_by_driver=driver.id,
            ),
        )
        return f"Baho #{rating.id} saqlandi ({score}/5)."

    # ── Admin ───────────────────────────────────────────

    async def get_ai_usage_stats(
        self, user_id: Optional[int] = None, date_iso: Optional[str] = None
    ) -> str:
        from datetime import date as _date

        target_date = _date.today()
        if date_iso:
            try:
                target_date = _date.fromisoformat(date_iso)
            except ValueError:
                return "date_iso noto'g'ri format (YYYY-MM-DD kerak)."

        stmt = select(AIUsage).where(AIUsage.usage_date == target_date)
        if user_id:
            stmt = stmt.where(AIUsage.user_id == user_id)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return f"{target_date} sanasida AI sarflari yo'q."
        return f"{target_date} statistikasi:\n" + "\n".join(
            f"- user#{r.user_id}: {r.requests} so'rov, in={r.input_tokens}, out={r.output_tokens}"
            for r in rows
        )

    async def list_available_models(self) -> str:
        current = await get_current_model()
        rows = "\n".join(
            f"- {'★ ' if m == current else '  '}{m}" for m in AVAILABLE_AI_MODELS
        )
        return f"Mavjud model'lar:\n{rows}\nJoriy: {current}"

    async def set_ai_model(self, model_name: str) -> str:
        if model_name not in AVAILABLE_AI_MODELS:
            return f"'{model_name}' ruxsat etilgan ro'yxatda emas: {AVAILABLE_AI_MODELS}"
        await set_current_model(model_name)
        return f"Joriy AI model: {model_name}."

    async def set_user_limit(self, user_id: int, daily_requests: int) -> str:
        if daily_requests < 0:
            return "Limit musbat son bo'lishi kerak."
        await set_user_limit_setting(self.db, user_id, daily_requests)
        return f"User #{user_id} limiti: {daily_requests}/kun."


# ════════════════════════════════════════════════════════════
# AGENT
# ════════════════════════════════════════════════════════════


ActionCallback = Optional[Callable[[str], Awaitable[None]]]


class LogistikaAgent:
    """Gemini AI Agent — role-aware, language-locked, async-safe."""

    def __init__(self, user_id: int, role: str = "guest", language: str = "uz"):
        self.user_id = user_id
        self.role = role or "guest"
        self.language = language or "uz"
        self.system_instruction = build_system_instruction(self.role, self.language)
        self.tools_decl = get_tools_for_role(self.role)

    # ── STT ─────────────────────────────────────────────

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str) -> str:
        """Audio -> matn (Gemini multimodal)."""
        if not client:
            return ""
        try:
            from google.genai import types  # type: ignore
        except Exception as exc:
            logger.error("google.genai.types import error: %s", exc)
            return ""

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = (
            "Transcribe this audio EXACTLY in the original spoken language. "
            "Output ONLY the raw transcript text, no markdown, no commentary."
        )
        model = await get_current_model()

        def _call() -> str:
            resp = client.models.generate_content(
                model=model,
                contents=[prompt, audio_part],
            )
            return (resp.text or "").strip()

        return await asyncio.to_thread(_call)

    # ── Asosiy oqim ────────────────────────────────────

    async def process_message(
        self,
        message_text: str,
        chat_id: int,
        on_action_callback: ActionCallback = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Foydalanuvchi xabarini qayta ishlaydi.

        Qaytaradi (response_text, usage_metadata).
        usage_metadata: {"input": int, "output": int, "total": int}.
        """
        empty_usage = {"input": 0, "output": 0, "total": 0}
        if not client:
            return ("AI Agent hozircha o'chiq (API_KEY sozlanmagan).", empty_usage)

        model = await get_current_model()
        config_obj: Dict[str, Any] = {"system_instruction": self.system_instruction}
        if self.tools_decl:
            config_obj["tools"] = [{"function_declarations": self.tools_decl}]

        try:
            response = await asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=model, contents=message_text, config=config_obj
                )
            )
        except Exception as exc:
            logger.error("AI Agent generate_content error: %s", exc)
            return (f"Kechirasiz, muammo yuz berdi: {exc}", empty_usage)

        usage = self._extract_usage(response)

        parts = (
            response.candidates[0].content.parts if response.candidates else None
        )
        function_call = None
        if parts:
            for p in parts:
                if getattr(p, "function_call", None):
                    function_call = p.function_call
                    break

        if function_call:
            func_name = function_call.name
            args = dict(function_call.args or {})

            if not _is_tool_allowed(func_name, self.role):
                return (
                    f"Sizning roleingiz ({self.role}) bu amalni bajarishga ruxsat bermaydi.",
                    usage,
                )

            if on_action_callback:
                await on_action_callback(f"Bajarilmoqda: {func_name}...")

            tool_def = _TOOL_BY_NAME[func_name]
            method_name = tool_def["method"]

            async with async_session() as db:
                result_user = await user_crud.get_user_by_id(db, self.user_id)
                if not result_user:
                    return ("Foydalanuvchi topilmadi.", usage)
                toolkit = LogistikaToolkit(db, result_user)
                tool_func = getattr(toolkit, method_name, None)
                if not tool_func:
                    return ("Tool implementatsiyasi topilmadi.", usage)
                try:
                    tool_result = await tool_func(**args)
                except TypeError as exc:
                    tool_result = f"Tool argumentlari xato: {exc}"
                except Exception as exc:
                    logger.error("Tool %s xatosi: %s", method_name, exc)
                    tool_result = f"Tool xatosi: {exc}"

            try:
                final_response = await asyncio.to_thread(
                    lambda: client.models.generate_content(
                        model=model,
                        contents=[
                            message_text,
                            response.candidates[0].content,
                            {
                                "parts": [
                                    {
                                        "function_response": {
                                            "name": func_name,
                                            "response": {"content": tool_result},
                                        }
                                    }
                                ]
                            },
                        ],
                        config=config_obj,
                    )
                )
            except Exception as exc:
                logger.error("AI final_response error: %s", exc)
                return (str(tool_result), usage)

            final_usage = self._extract_usage(final_response)
            for k in usage:
                usage[k] += final_usage.get(k, 0)
            return (final_response.text or str(tool_result), usage)

        return (response.text or "", usage)

    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, int]:
        meta = getattr(response, "usage_metadata", None)
        if not meta:
            return {"input": 0, "output": 0, "total": 0}
        return {
            "input": int(getattr(meta, "prompt_token_count", 0) or 0),
            "output": int(getattr(meta, "candidates_token_count", 0) or 0),
            "total": int(getattr(meta, "total_token_count", 0) or 0),
        }
