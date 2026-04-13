from aiogram import Router, types
from aiogram.filters import CommandStart

import database as db

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    tg_user = message.from_user

    lang = tg_user.language_code if tg_user.language_code in ("uz", "ru") else "uz"

    user, created = await db.get_or_create_user(
        user_id=tg_user.id,
        full_name=tg_user.full_name,
        username=tg_user.username,
        language=lang,
    )

    if created:
        await message.answer(
            f"Xush kelibsiz, {tg_user.full_name}! 👋\n"
            f"Siz ro'yxatdan o'tdingiz."
        )
    else:
        await message.answer(
            f"Salom, {tg_user.full_name}! 👋\n"
            f"Botga qaytib kelganingizdan xursandmiz."
        )
