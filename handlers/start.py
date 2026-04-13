from aiogram import Router, types, F
from aiogram.filters import CommandStart

from keyboards.reply import get_language_keyboard
import database as db

router = Router()

# Til tugmalari matni → kod
LANG_MAP = {
    "🇺🇿 O'zbekcha": "uz",
    "🇷🇺 Русский": "ru",
}


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = await db.get_user(message.from_user.id)

    if user:
        # Mavjud user — tilini qayta tanlashi mumkin
        greet = "Assalomu alaykum" if user.language == "uz" else "Добро пожаловать обратно"
        await message.answer(
            f"{greet}, {message.from_user.full_name}! 👋\n"
            f"Tilni o'zgartirish uchun / Чтобы сменить язык:",
            reply_markup=get_language_keyboard()
        )
    else:
        # Yangi user — til tanlash
        await message.answer(
            "Tilni tanlang / Выберите язык:",
            reply_markup=get_language_keyboard()
        )


@router.message(F.text.in_(LANG_MAP.keys()))
async def select_language(message: types.Message):
    tg_user = message.from_user
    lang = LANG_MAP[message.text]  # "uz" yoki "ru"

    user = await db.get_user(tg_user.id)

    if user:
        # Mavjud user — faqat tilini yangilash
        await db.update_user_language(tg_user.id, lang)
        if lang == "uz":
            await message.answer(
                f"✅ Til o'zbekchaga o'rnatildi, {tg_user.full_name}!",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.answer(
                f"✅ Язык установлен на русский, {tg_user.full_name}!",
                reply_markup=types.ReplyKeyboardRemove()
            )
    else:
        # Yangi user — yaratish
        await db.create_user(
            user_id=tg_user.id,
            full_name=tg_user.full_name,
            username=tg_user.username,
            language=lang,
        )
        if lang == "uz":
            await message.answer(
                f"✅ Ro'yxatdan o'tdingiz, {tg_user.full_name}!\n"
                f"Til: O'zbekcha 🇺🇿",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.answer(
                f"✅ Вы зарегистрированы, {tg_user.full_name}!\n"
                f"Язык: Русский 🇷🇺",
                reply_markup=types.ReplyKeyboardRemove()
            )
