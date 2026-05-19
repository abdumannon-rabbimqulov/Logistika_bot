import asyncio
import logging



from config.config import  engine
from handlers import main_router

from aiogram import Dispatcher
from handlers.bot import bot


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

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

