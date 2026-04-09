import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Integer, BigInteger, String, Float,
    DateTime, ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base


# ─────────────────────────────────────────────────────────────
# Intent turlari — har bir so'rov shu categoriyalardan biriga
# ─────────────────────────────────────────────────────────────

class IntentType(enum.Enum):
    COMPLAINT      = "complaint"       # "Haydovchi kech keldi", "yuk buzilgan"
    SUGGESTION     = "suggestion"      # "Ilovaga xarita qo'shing"
    PRICE_QUERY    = "price_query"     # "Toshkent-Samarqand necha so'm?"
    FIND_DRIVER    = "find_driver"     # "10 tonnalik fura kerak"
    TRACK_ORDER    = "track_order"     # "Yukum qayerda?", "qachon yetadi?"
    CREATE_ORDER   = "create_order"    # Yangi buyurtma bermoqchi
    DRIVER_SIGNUP  = "driver_signup"   # Haydovchi ro'yxatdan o'tmoqchi
    CANCEL_ORDER   = "cancel_order"    # Buyurtmani bekor qilmoqchi
    PAYMENT        = "payment"         # To'lov haqida savol
    GENERAL_INFO   = "general_info"    # Umumiy savol, salomlashish
    UNKNOWN        = "unknown"         # Aniqlab bo'lmadi


# ─────────────────────────────────────────────────────────────
# IntentLog — har bir xabar uchun router natijasi saqlanadi
# (model ishlashini kuzatish + retraining uchun)
# ─────────────────────────────────────────────────────────────

class IntentLog(Base):
    __tablename__ = "intent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Kim yozdi
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Xabar matni
    message_text: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Router natijasi
    predicted_intent: Mapped[IntentType] = mapped_column(SQLEnum(IntentType), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 – 1.0

    # Agar foydalanuvchi tuzatgan bo'lsa (feedback loop uchun)
    corrected_intent: Mapped[IntentType | None] = mapped_column(SQLEnum(IntentType), nullable=True)

    # Qaysi modelga yuborildi
    routed_to: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Model versiyasi (retraining tarixini kuzatish)
    model_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Qo'shimcha meta (entities, keywords va h.k.)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<IntentLog(user={self.user_id}, "
            f"intent={self.predicted_intent.value}, "
            f"conf={self.confidence:.2f})>"
        )


# ─────────────────────────────────────────────────────────────
# Intent Router handler — Anthropic API orqali ishlaydi
# ─────────────────────────────────────────────────────────────

import json
import httpx
from dataclasses import dataclass


@dataclass
class RouterResult:
    intent: IntentType
    confidence: float
    entities: dict        # e.g. {"from_city": "Toshkent", "to_city": "Samarqand"}
    needs_clarification: bool
    clarification_text: str | None = None


SYSTEM_PROMPT = """Siz logistika Telegram botining Intent Router sizmiz.
Foydalanuvchi xabarini o'qib, quyidagi JSON formatda javob bering:

{
  "intent": "<intent_type>",
  "confidence": <0.0-1.0>,
  "entities": {<ajratilgan ma'lumotlar>}
}

Intent turlari:
- complaint      : shikoyat (kechikish, haydovchi muammosi, yuk buzilishi)
- suggestion     : taklif (xizmat yaxshilash, yangi funksiya)
- price_query    : narx so'rovi (shahar juftligi, yuk og'irligi)
- find_driver    : haydovchi qidirish (truck turi, yuk hajmi)
- track_order    : buyurtma holati, ETA, joylashuv
- create_order   : yangi buyurtma yaratish
- driver_signup  : haydovchi ro'yxatdan o'tish
- cancel_order   : buyurtma bekor qilish
- payment        : to'lov, hisob-kitob
- general_info   : salomlashish, umumiy savol
- unknown        : aniqlab bo'lmadi

Entities misollari:
- price_query: {"from_city": "Toshkent", "to_city": "Buxoro", "weight_ton": 5}
- find_driver: {"truck_type": "tent", "weight_ton": 10, "from_city": "Andijon"}
- complaint:   {"issue_type": "delay", "order_id": null}

Faqat JSON qaytaring, boshqa hech narsa yozmang."""


async def route_intent(message: str, user_id: int) -> RouterResult:
    """
    User xabarini Intent Router AI ga yuboradi va natijani qaytaradi.

    Ishlatish:
        result = await route_intent("Toshkent-Samarqand narx?", user_id=123)
        if result.intent == IntentType.PRICE_QUERY:
            await handle_price_query(result.entities)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": "YOUR_API_KEY",        # env dan oling
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",  # tez va arzon
                "max_tokens": 256,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": message}
                ],
            },
            timeout=10.0,
        )
        data = response.json()

    raw = data["content"][0]["text"].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return RouterResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            entities={},
            needs_clarification=False,
        )

    intent_str  = parsed.get("intent", "unknown")
    confidence  = float(parsed.get("confidence", 0.0))
    entities    = parsed.get("entities", {})

    try:
        intent = IntentType(intent_str)
    except ValueError:
        intent = IntentType.UNKNOWN

    # Ishonch past bo'lsa — foydalanuvchidan aniqlash so'raladi
    needs_clarification = confidence < 0.6 or intent == IntentType.UNKNOWN

    clarification_text = None
    if needs_clarification:
        clarification_text = _build_clarification(intent, entities)

    return RouterResult(
        intent=intent,
        confidence=confidence,
        entities=entities,
        needs_clarification=needs_clarification,
        clarification_text=clarification_text,
    )


def _build_clarification(intent: IntentType, entities: dict) -> str:
    """Intent noaniq bo'lganda foydalanuvchiga beriladigan savol."""
    messages = {
        IntentType.UNKNOWN:   "Kechirasiz, tushunmadim. Shikoyat, taklif yoki buyurtma haqidami?",
        IntentType.COMPLAINT: "Bu shikoyatmi yoki haydovchi haqida taklif?",
        IntentType.PRICE_QUERY: "Qayerdan qayerga va necha tonna yuk bor?",
        IntentType.FIND_DRIVER: "Qanday mashina kerak va qancha yuk bor?",
    }
    return messages.get(intent, "Iltimos, aniqroq yozing.")


# ─────────────────────────────────────────────────────────────
# Dispatcher — natijaga qarab to'g'ri handlerga yo'naltiradi
# ─────────────────────────────────────────────────────────────

async def dispatch(result: RouterResult, user_id: int, message: str):
    """
    RouterResult ga qarab tegishli handler chaqiriladi.
    Bu funksiyani aiogram handler ichidan chaqiring.

    Misol (aiogram):
        @router.message()
        async def handle_any(message: Message):
            result = await route_intent(message.text, message.from_user.id)
            await dispatch(result, message.from_user.id, message.text)
    """
    if result.needs_clarification:
        # Foydalanuvchidan aniqlashtirish so'raladi
        # await bot.send_message(user_id, result.clarification_text)
        return

    handlers = {
        IntentType.COMPLAINT:    handle_complaint,
        IntentType.SUGGESTION:   handle_suggestion,
        IntentType.PRICE_QUERY:  handle_price_query,
        IntentType.FIND_DRIVER:  handle_find_driver,
        IntentType.TRACK_ORDER:  handle_track_order,
        IntentType.CREATE_ORDER: handle_create_order,
        IntentType.CANCEL_ORDER: handle_cancel_order,
        IntentType.PAYMENT:      handle_payment,
        IntentType.GENERAL_INFO: handle_general_info,
        IntentType.UNKNOWN:      handle_unknown,
    }

    handler = handlers.get(result.intent, handle_unknown)
    await handler(user_id=user_id, entities=result.entities, raw_message=message)


# ─────────────────────────────────────────────────────────────
# Stub handlerlar — har birini o'z faylingizda implement qiling
# ─────────────────────────────────────────────────────────────

async def handle_complaint(user_id: int, entities: dict, raw_message: str):
    """→ complaint.py ga o'tkaziladi"""
    pass

async def handle_suggestion(user_id: int, entities: dict, raw_message: str):
    """→ suggestion.py ga o'tkaziladi"""
    pass

async def handle_price_query(user_id: int, entities: dict, raw_message: str):
    """→ price_ai.py ga o'tkaziladi"""
    pass

async def handle_find_driver(user_id: int, entities: dict, raw_message: str):
    """→ driver_match.py ga o'tkaziladi"""
    pass

async def handle_track_order(user_id: int, entities: dict, raw_message: str):
    """→ eta_prediction.py ga o'tkaziladi"""
    pass

async def handle_create_order(user_id: int, entities: dict, raw_message: str):
    pass

async def handle_cancel_order(user_id: int, entities: dict, raw_message: str):
    pass

async def handle_payment(user_id: int, entities: dict, raw_message: str):
    pass

async def handle_general_info(user_id: int, entities: dict, raw_message: str):
    pass

async def handle_unknown(user_id: int, entities: dict, raw_message: str):
    pass