"""Driver Telegram bot live location handler.

Foydalanuvchi (driver) `📍 Live lokatsiya yuborish` tugmasini bosadi va
Telegramning native "Share My Live Location" oqimi orqali davriy yangilanish
yuboradi. Bot har xabarni `services.live_location.update_driver_location` ga
uzatadi (Redis + Postgres throttle).
"""

from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from config.config import async_session
from driver import crud as driver_crud
from services import live_location
from users.models import UserRole
import database as db

logger = logging.getLogger(__name__)
router = Router()


# ── Reply tugmalar matni (3 til) ─────────────────────────────
LIVE_BTN_TEXTS = {
    "uz":      "📍 Jonli lokatsiya yuborish (yo'riqnoma)",
    "uz_cyrl": "📍 Жонли локацияни юбориш (йўриқнома)",
    "ru":      "📍 Отправить live-локацию (инструкция)",
}

LIVE_HOWTO_TEXT = {
    "uz": (
        "📍 *Jonli lokatsiya yuborish*\n\n"
        "1. Pastdagi 📎 (skripka) tugmasini bosing\n"
        "2. *Location* / *Lokatsiya* ni tanlang\n"
        "3. *Share My Live Location for...* ni bosing\n"
        "4. *1 hour* ni tanlang\n\n"
        "Tizim har soatda joylashuvingizni yangilab turadi."
    ),
    "uz_cyrl": (
        "📍 *Жонли локацияни юбориш*\n\n"
        "1. Пастдаги 📎 (скрипка) тугмасини босинг\n"
        "2. *Локация* ни танланг\n"
        "3. *Share My Live Location for...* ни босинг\n"
        "4. *1 hour* ни танланг\n\n"
        "Тизим ҳар соатда жойлашувингизни янгилаб туради."
    ),
    "ru": (
        "📍 *Отправка live-локации*\n\n"
        "1. Нажмите 📎 (скрепка) внизу\n"
        "2. Выберите *Геопозиция*\n"
        "3. Нажмите *Транслировать мою геопозицию...*\n"
        "4. Выберите *1 час*\n\n"
        "Система будет обновлять вашу позицию автоматически."
    ),
}


def driver_keyboard(lang: str) -> types.ReplyKeyboardMarkup:
    text = LIVE_BTN_TEXTS.get(lang, LIVE_BTN_TEXTS["uz"])
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=text)]],
        resize_keyboard=True,
    )


# ── Yo'riqnoma matni ────────────────────────────────────────
@router.message(F.text.in_(set(LIVE_BTN_TEXTS.values())))
async def show_live_howto(message: types.Message) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    await message.answer(
        LIVE_HOWTO_TEXT.get(lang, LIVE_HOWTO_TEXT["uz"]),
        parse_mode="Markdown",
    )


@router.message(Command("live"))
async def cmd_live(message: types.Message) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    if not user or user.role != UserRole.DRIVER:
        await message.answer("Bu buyruq faqat haydovchilar uchun.")
        return
    await message.answer(
        LIVE_HOWTO_TEXT.get(lang, LIVE_HOWTO_TEXT["uz"]),
        parse_mode="Markdown",
        reply_markup=driver_keyboard(lang),
    )


# ── Lokatsiya event'lari ────────────────────────────────────
async def _handle_location_event(message: types.Message) -> None:
    if message.location is None:
        return

    user = await db.get_user(message.from_user.id)
    if not user:
        return
    if user.role != UserRole.DRIVER:
        # Driver bo'lmasa jim bo'lib qaytamiz (boshqa rol uchun ishlatilmaydi)
        return

    async with async_session() as session:
        driver = await driver_crud.get_driver_by_user_id(session, user.id)

    if not driver:
        await message.answer(
            "Driver profili topilmadi. Avval haydovchi profilingizni to'ldiring."
        )
        return
    if driver.is_blocked:
        await message.answer("Sizning haydovchi profilingiz bloklangan.")
        return

    loc = message.location
    live_period = int(loc.live_period or 0)

    if live_period == 0:
        # Telegram "stop sharing" yuborganda live_period=0; bu vaqtinchalik to'xtatish demak
        await live_location.stop_driver_location(driver.id)
        if message.from_user.id == message.chat.id:
            await message.answer("📍 Live lokatsiya to'xtatildi.")
        return

    truck_type_id = getattr(driver, "truck_type_id", None)
    payload = await live_location.update_driver_location(
        driver_id=driver.id,
        lat=float(loc.latitude),
        lon=float(loc.longitude),
        user_id=user.id,
        full_name=user.full_name,
        truck_number=driver.truck_number,
        truck_type_id=truck_type_id,
        live_period=live_period,
    )
    logger.debug("driver_location_update %s", payload)


@router.message(F.location)
async def on_location_message(message: types.Message) -> None:
    await _handle_location_event(message)


@router.edited_message(F.location)
async def on_location_edited(message: types.Message) -> None:
    await _handle_location_event(message)
