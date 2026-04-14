from aiogram import Router, types, F
from aiogram.filters import Command
from config.config import is_admin, WEBAPP_URL, create_access_token
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

router = Router()

@router.message(Command("admin"))
async def admin_command(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    token, expires = create_access_token({"sub": str(user_id), "role": "admin"})

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Admin Dashboard",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/?token={token}")
        )]
    ])

    await message.answer(
        "Xush kelibsiz, Admin! 👋\nQuyidagi tugma orqali boshqaruv paneliga kiring (Token yangilandi):",
        reply_markup=kb
    )
