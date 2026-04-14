from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.reply import get_language_keyboard, get_phone_keyboard
from config.config import create_access_token
import database as db

router = Router()

class Registration(StatesGroup):
    language = State()
    phone_number = State()

LANG_MAP = {
    "🇺🇿 O'zbekcha": "uz",
    "🇷🇺 Русский": "ru",
}


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):

    user = await db.get_user(message.from_user.id)

    if user and user.phone_number:
        token, expires = create_access_token({"sub": str(message.from_user.id), "role": user.role or "guest"})
        await db.update_user_token(message.from_user.id, token, expires)

        greet = "Assalomu alaykum" if user.language == "uz" else "Здравствуйте"
        await message.answer(
            f"{greet}, {message.from_user.full_name}! 👋\n"
            f"Sizga qanday yordam bera olaman?" if user.language == "uz" else "Чем могу помочь?",
            reply_markup=types.ReplyKeyboardRemove()
        )
        # Kelajakda bu yerda asosiy menyu chiqadi
    else:
        # Til tanlashni so'rash
        await message.answer(
            "Assalomu alaykum! Botdan foydalanish uchun tilni tanlang:\n"
            "Здравствуйте! Для использования бота выберите язык:",
            reply_markup=get_language_keyboard()
        )
        await state.set_state(Registration.language)


@router.message(Registration.language, F.text.in_(LANG_MAP.keys()))
async def select_language(message: types.Message, state: FSMContext):
    """Tilni saqlash va telefon raqamini so'rash."""
    lang = LANG_MAP[message.text]
    await state.update_data(language=lang)
    
    # Telefon raqamini so'rash
    text = (
        "Rahmat! Endi telefon raqamingizni yuboring (pastdagi tugmani bosing):" 
        if lang == "uz" else 
        "Спасибо! Теперь отправьте ваш номер телефона (нажмите кнопку ниже):"
    )
    await message.answer(text, reply_markup=get_phone_keyboard(lang))
    await state.set_state(Registration.phone_number)


@router.message(Registration.phone_number, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    """Telefon raqamini saqlash va ro'yxatdan o'tishni yakunlash."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    phone = message.contact.phone_number
    
    tg_user = message.from_user
    user = await db.get_user(tg_user.id)
    
    if not user:
        # Yangi foydalanuvchi yaratish
        await db.create_user(
            user_id=tg_user.id,
            full_name=tg_user.full_name,
            username=tg_user.username,
            language=lang,
        )
    
    # Telefon raqami va tilni yangilash
    await db.update_user_language(tg_user.id, lang)
    await db.update_user_phone(tg_user.id, phone)
    
    # Token yaratish (Web App uchun)
    token, expires = create_access_token({"sub": str(tg_user.id), "role": user.role if user else "guest"})
    await db.update_user_token(tg_user.id, token, expires)
    
    # Muvaffaqiyatli yakunlash
    text = (
        f"✅ Ro'yxatdan o'tdingiz, {tg_user.full_name}!\n"
        f"Endi bot xizmatlaridan foydalanishingiz mumkin."
        if lang == "uz" else
        f"✅ Вы успешно зарегистрированы, {tg_user.full_name}!\n"
        f"Теперь вы можете пользоваться услугами бота."
    )
    await message.answer(text, reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@router.message(Registration.language)
@router.message(Registration.phone_number)
async def skip_registration(message: types.Message):
    """Ro'yxatdan o'tish paytida boshqa narsa yozsa qayta so'rash."""
    await message.answer("Iltimos, ro'yxatdan o'tishni yakunlang (kerakli tugmani bosing).")
