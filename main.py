import asyncio
import logging



from config.config import  engine
from config import registry
import driver.models
import order.models
import order.dispatch_models
import users.models
from sqlalchemy.orm import configure_mappers
configure_mappers()

from handlers import main_router

from aiogram import Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo
from handlers.bot import bot
from config.config import WEBAPP_URL


async def _setup_menu_button() -> None:
    """Mini App'ni istalgan foydalanuvchi (hali /start bosmagan GUEST ham) doim
    ko'radigan tugma orqali ochsin — chat menyusidagi doimiy tugma sifatida
    o'rnatiladi (faqat bitta marta, bot ishga tushganda). Faqat HTTPS'da ishlaydi,
    aks holda (lokal/dev) jim o'tkazib yuboriladi."""
    if not WEBAPP_URL.startswith("https://"):
        logging.warning("WEBAPP_URL https emas — Mini App menyu tugmasi o'rnatilmadi (%s)", WEBAPP_URL)
        return
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Yuk ilovasi", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    except Exception:
        logging.exception("Mini App menyu tugmasini o'rnatib bo'lmadi")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    dp = Dispatcher()            # Event dispatcher

    dp.include_router(main_router)   # Barcha handlerlarni ulash

    try:
        logging.info("🚀 Bot ishga tushirildi...")
        await bot.delete_webhook(drop_pending_updates=True)  # Webhookni o'chirish va kutayotgan yangilanishlarni tozalash
        await _setup_menu_button()
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

