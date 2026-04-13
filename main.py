import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from config.config import BOT_TOKEN, API_KEY
from handlers import main_router
from middlewares.i18n import I18nMiddleware
from middlewares.logging import ShadowLoggingMiddleware
from ai.db import db

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.middleware(ShadowLoggingMiddleware())
    dp.callback_query.middleware(ShadowLoggingMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    dp.include_router(main_router)


    await db.connect()

    try:
        logging.info("🚀 Bot ishga tushirildi...")
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("⏹ Bot to'xtatildi")
