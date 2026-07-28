#!/usr/bin/env python3
"""
Sinov (test) uchun bitta haydovchi yaratadi.

Ishlatish:
  docker compose exec web python scripts/seed_test_driver.py

Skript IDEMPOTENT: qayta ishga tushirilsa dublikat yaratmaydi, mavjud yozuvni
kerakli holatga keltiradi (parol, rol, tasdiqlangan hujjatlar va h.k.).

Yaratiladigan hisob:
  telefon : +998901112233
  parol   : Test1234
  rol     : driver

Telegram ID sifatida ataylab "soxta" diapazon (999000001) ishlatiladi — haqiqiy
Telegram akkaunt ID'lari bilan to'qnashmasligi uchun. Bu shuni anglatadiki, bu
hisobga faqat Mini App'ning telefon+parol oqimi orqali kirish mumkin (Telegram
initData bilan emas) — sinov uchun aynan shu kerak.

O'chirish:
  docker compose exec web python scripts/seed_test_driver.py --delete
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from config.config import async_session  # noqa: E402
from driver.models import Driver, DriverVerificationStatus, TruckType  # noqa: E402
from users.auth import hash_password  # noqa: E402
from users.models import User, UserRole  # noqa: E402
from utils.validation import normalize_phone_number  # noqa: E402

TELEGRAM_ID = 999_000_001
FULL_NAME = "Test Haydovchi"
USERNAME = "test_driver"
PHONE = "+998901112233"
PASSWORD = "Test1234"
TRUCK_NUMBER = "01T001TS"
CITY = "Toshkent"
REGION = "Toshkent shahri"


async def seed() -> None:
    phone = normalize_phone_number(PHONE)

    async with async_session() as db:
        # Telefon raqami boshqa (begona) foydalanuvchida band bo'lsa to'xtaymiz —
        # jimgina ustiga yozib, haqiqiy hisobni buzib qo'ymaslik uchun.
        clash = await db.scalar(
            select(User).where(User.phone_number == phone, User.id != TELEGRAM_ID)
        )
        if clash:
            raise SystemExit(
                f"❌ {phone} raqami allaqachon boshqa foydalanuvchida band "
                f"(id={clash.id}, {clash.full_name}). To'xtatildi."
            )

        truck_type = await db.scalar(
            select(TruckType).where(TruckType.is_active.is_(True)).order_by(TruckType.id)
        )
        if truck_type is None:
            raise SystemExit(
                "❌ Bazada birorta faol truck_type yo'q — avval admin panelda "
                "mashina turi qo'shing (haydovchi unga bog'lanishi shart)."
            )

        user = await db.get(User, TELEGRAM_ID)
        if user is None:
            user = User(id=TELEGRAM_ID)
            db.add(user)
            created_user = True
        else:
            created_user = False

        user.full_name = FULL_NAME
        user.username = USERNAME
        user.phone_number = phone
        user.password = hash_password(PASSWORD)
        user.role = UserRole.DRIVER
        user.language = "uz"
        user.is_active = True
        user.is_banned = False

        await db.flush()  # drivers.user_id uchun user qatori mavjud bo'lsin

        driver = await db.scalar(select(Driver).where(Driver.user_id == TELEGRAM_ID))
        if driver is None:
            driver = Driver(user_id=TELEGRAM_ID)
            db.add(driver)
            created_driver = True
        else:
            created_driver = False

        driver.truck_type_id = truck_type.id
        driver.truck_number = TRUCK_NUMBER
        driver.truck_year = 2020
        driver.current_city = CITY
        driver.current_region = REGION
        # Sinovda darhol buyurtma olishi uchun: tasdiqlangan va liniyada.
        driver.docs_verified = True
        driver.verification_status = DriverVerificationStatus.APPROVED
        driver.is_available = True
        driver.is_blocked = False

        await db.commit()

    print("✅ Sinov haydovchisi tayyor")
    print(f"   user   : {'yaratildi' if created_user else 'yangilandi'} (id={TELEGRAM_ID})")
    print(f"   driver : {'yaratildi' if created_driver else 'yangilandi'}")
    print(f"   telefon: {phone}")
    print(f"   parol  : {PASSWORD}")
    print(f"   mashina: {truck_type.name} · {TRUCK_NUMBER}")


async def delete() -> None:
    async with async_session() as db:
        driver = await db.scalar(select(Driver).where(Driver.user_id == TELEGRAM_ID))
        if driver:
            await db.delete(driver)
        user = await db.get(User, TELEGRAM_ID)
        if user:
            await db.delete(user)
        await db.commit()
    print(f"🗑  Sinov haydovchisi o'chirildi (id={TELEGRAM_ID})")


if __name__ == "__main__":
    asyncio.run(delete() if "--delete" in sys.argv else seed())
