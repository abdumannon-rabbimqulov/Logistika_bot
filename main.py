import asyncio
import logging

from aiogram import Bot, Dispatcher
from config.config import BOT_TOKEN, engine
from handlers import main_router


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(main_router)

    try:
        logging.info("🚀 Bot ishga tushirildi...")
        await dp.start_polling(bot)
    finally:
        await engine.dispose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("⏹ Bot to'xtatildi")
