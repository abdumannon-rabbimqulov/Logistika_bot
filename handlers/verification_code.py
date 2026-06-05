import secrets

from aiogram import Router, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton

router = Router()


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def send_verification_code(bot: Bot, telegram_id: int) -> str:
    code = generate_code()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Kodni nusxalash",
                    copy_text=CopyTextButton(text=code)
                )
            ]
        ]
    )

    await bot.send_message(
        chat_id=telegram_id,
        text=f"🔐 Tasdiqlash kodingiz:\n\n<code>{code}</code>\n\nKod 2 daqiqa amal qiladi.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    print(f"Generated verification code for Telegram ID {telegram_id}: {code}------------------")

    return code

