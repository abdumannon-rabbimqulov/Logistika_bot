import asyncio
import logging

# ──────────────────────────────────────────────────────────────────────────────
# TELEGRAM BOT INTEGRATSIYASI
# ──────────────────────────────────────────────────────────────────────────────
# Quyidagi importlar Telegram bot bilan bog'liq.
# Faqat bot rejimida ishlatiladi.
# Agar faqat FastAPI (REST API) ishlatmoqchi bo'lsangiz:
#   1. Quyidagi 3 qatorni comment ga oling
#   2. config/config.py da BOT_TOKEN tekshiruvini ham comment ga oling
# ──────────────────────────────────────────────────────────────────────────────
from aiogram import Bot, Dispatcher                  # Telegram bot kutubxonasi
from config.config import BOT_TOKEN, engine          # Bot token va DB engine
from handlers import main_router                     # Bot handlerlari


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # ── Telegram bot obyektlari ──────────────────────────────────────────────
    bot = Bot(token=BOT_TOKEN)   # Telegram Bot
    dp = Dispatcher()            # Event dispatcher

    dp.include_router(main_router)   # Barcha handlerlarni ulash

    try:
        logging.info("🚀 Bot ishga tushirildi...")
        await dp.start_polling(bot)   # Bot polling rejimida ishlaydi
    finally:
        # ── Chiqishda resurslarni tozalash ───────────────────────────────────
        await engine.dispose()        # DB ulanishlarini yopish
        await bot.session.close()     # HTTP sessiyani yopish


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("⏹ Bot to'xtatildi")

