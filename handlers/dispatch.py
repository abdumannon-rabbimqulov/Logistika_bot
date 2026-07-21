"""Avtomatik dispatch: haydovchi Telegram bot orqali "Qabul qilish/Rad etish" tugmalarini
bossa shu yerga keladi. Xuddi shu mantiq WebApp uchun `order/router.py`dagi
`POST /orders/dispatch/{attempt_id}/accept|reject` orqali ham ishlaydi — ikkalasi ham
`services/dispatch.py`ni chaqiradi (docs/DISPATCH_SYSTEM_PLAN.md, 8-bo'lim: "kod
takrorlanmasligi uchun umumiy servis").
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.types import CallbackQuery

import driver.crud as driver_crud
import order.crud as order_crud
from config.config import async_session
from driver.schemas import DriverUpdate
from services import dispatch as dispatch_service, notifications
from services.dispatch import DispatchError

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("dispatch:accept:"))
async def on_dispatch_accept(callback: CallbackQuery) -> None:
    attempt_id = int(callback.data.split(":")[2])
    async with async_session() as db:
        try:
            await dispatch_service.accept_attempt(db, attempt_id, acting_user_id=callback.from_user.id)
        except DispatchError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except Exception:
            logger.exception("dispatch:accept callback xatosi (attempt_id=%s)", attempt_id)
            await callback.answer("Xatolik yuz berdi, keyinroq urinib ko'ring", show_alert=True)
            return
    await callback.answer("✅ Qabul qilindi!")

    # Majburiy emas — shunchaki qulaylik uchun so'raladi: yangi buyurtma bilan band
    # bo'lgani uchun boshqa takliflar kelmasligini xohlashi mumkin.
    keyboard = notifications.inline_keyboard(
        [[("✅ Ha, chiqaman", "goinactive:yes"), ("Yo'q, liniyada qolaman", "goinactive:no")]]
    )
    await notifications.send_telegram_message(
        callback.from_user.id,
        "Liniyadan vaqtincha chiqasizmi (yangi takliflar kelmasligi uchun)?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("goinactive:"))
async def on_go_inactive_response(callback: CallbackQuery) -> None:
    answer = callback.data.split(":", 1)[1]
    if answer == "yes":
        async with async_session() as db:
            driver = await driver_crud.get_driver_by_user_id(db, callback.from_user.id)
            if driver:
                await driver_crud.update_driver(db, driver.id, DriverUpdate(is_available=False))
        await callback.answer("Liniyadan chiqdingiz")
    else:
        await callback.answer("Liniyada qoldingiz")

    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


@router.callback_query(F.data.startswith("dispatch:reject:"))
async def on_dispatch_reject(callback: CallbackQuery) -> None:
    attempt_id = int(callback.data.split(":")[2])
    async with async_session() as db:
        try:
            await dispatch_service.reject_attempt(db, attempt_id, acting_user_id=callback.from_user.id)
        except DispatchError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except Exception:
            logger.exception("dispatch:reject callback xatosi (attempt_id=%s)", attempt_id)
            await callback.answer("Xatolik yuz berdi, keyinroq urinib ko'ring", show_alert=True)
            return
    await callback.answer("Rad etildi")


@router.callback_query(F.data.startswith("pricebump:"))
async def on_price_bump(callback: CallbackQuery) -> None:
    try:
        _, order_id_str, price_str = callback.data.split(":")
        order_id = int(order_id_str)
        new_price = Decimal(price_str)
    except (ValueError, InvalidOperation):
        await callback.answer("Noto'g'ri so'rov", show_alert=True)
        return

    async with async_session() as db:
        order = await order_crud.get_order(db, order_id)
        if not order or order.customer_id != callback.from_user.id:
            await callback.answer("Bu buyurtma sizga tegishli emas", show_alert=True)
            return
        try:
            await dispatch_service.apply_price_bump(db, order, new_price)
        except DispatchError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except Exception:
            logger.exception("pricebump callback xatosi (order_id=%s)", order_id)
            await callback.answer("Xatolik yuz berdi, keyinroq urinib ko'ring", show_alert=True)
            return

    await callback.answer("✅ Narx yangilandi, qidiruv davom etmoqda")
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
