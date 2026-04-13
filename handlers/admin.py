from aiogram import Router, types, F
from aiogram.filters import Command
from config.config import is_admin, WEBAPP_URL
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

router = Router()

@router.message(Command("admin"))
async def admin_command(message: types.Message):
    """Admin panelga kirish buyrug'i."""
    if not is_admin(message.from_user.id, message.from_user.username):
        return  # Admin bo'lmasa javob bermaymiz

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Admin Dashboard",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/")
        )]
    ])

    await message.answer(
        "Xush kelibsiz, Admin! 👋\nQuyidagi tugma orqali boshqaruv paneliga kiring:",
        reply_markup=kb
    )
