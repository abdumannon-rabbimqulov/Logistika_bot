import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN,API_KEY
from handlers import main_router
from db import db
from middlewares.i18n import I18nMiddleware
from middlewares.logging import ShadowLoggingMiddleware

async def main():
    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register middlewares
    dp.message.middleware(ShadowLoggingMiddleware())
    dp.callback_query.middleware(ShadowLoggingMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    # Include routers
    dp.include_router(main_router)

    # Catch-all handler for debugging
    # @dp.message()
    # async def echo_handler(message: types.Message):
    #     logging.warning(f"❌ [UNHANDLED] From {message.from_user.id}: {message.text}")
    #     await message.answer("Tushunarsiz buyruq. /start bosing.")

    # Connect to database
    await db.connect()

    try:
        logging.info("🚀 Bot ishga tushirildi...")
        await dp.start_polling(bot)
    finally:
        # Close database connection on exit
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("⏹ Bot to'xtatildi")
