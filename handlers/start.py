from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from users.models import UserRole

from keyboards.reply import (
    get_language_keyboard,
    get_phone_keyboard,
    get_role_keyboard,
)
from users.models import UserRole
import database as db
from utils.validation import normalize_phone_number

import os
from dotenv import load_dotenv

load_dotenv()

router = Router()


ADMIN_ID=int(os.getenv("ADMIN", 0))

class Registration(StatesGroup):
    language = State()
    phone_number = State()
    role = State()


LANG_MAP = {
    "🇺🇿 O'zbekcha": "uz",
    "🇺🇿 Ўзбекча": "uz_cyrl",
    "🇷🇺 Русский": "ru",
}

ROLE_MAP = {
    "📦 Отправитель груза": UserRole.SENDER,
    "🚛 Водитель": UserRole.DRIVER,
    "📦 Юк берувчи": UserRole.SENDER,
    "🚛 Ҳайдовчи": UserRole.DRIVER,
    "📦 Yuk beruvchi": UserRole.SENDER,
    "🚛 Haydovchi": UserRole.DRIVER,
}


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # FSM holatini tozalaymiz, agar adashib qolgan bo'lsa boshidan boshlashi uchun
    await state.clear()
    tg_id = message.from_user.id
    user = await db.get_user(tg_id)

    if tg_id == ADMIN_ID:
        if not user:
            user = await db.create_user(
                user_id=tg_id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                language="uz",
                phone_number=None,
                role=UserRole.ADMIN
            )
        elif getattr(user, 'role', None) != UserRole.ADMIN:
            await db.update_user_profile_from_tg(
                user_id=tg_id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                language=user.language,
                phone_number=user.phone_number,
                role=UserRole.ADMIN
            )
            user = await db.get_user(tg_id)
        
        await message.answer(
            f"Assalomu alaykum Admin, {message.from_user.full_name}!\n"
            "Tizimga kirishga ruxsat berildi. Boshqaruv paneli huquqlari ochildi.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    if user and user.phone_number:
        if user.language == "ru":
            greet = "Здравствуйте"
            help_text = "Чем могу помочь?"
        elif user.language == "uz_cyrl":
            greet = "Ассалому алайкум"
            help_text = "Сизга қандай ёрдам бера оламан?"
        else:
            greet = "Assalomu alaykum"
            help_text = "Sizga qanday yordam bera olaman?"

        # TUZATILDI: Foydalanuvchiga javob yuborish qo'shildi
        await message.answer(f"{greet}, {message.from_user.full_name}!\n{help_text}")
    else:
        await message.answer(
            "Assalomu alaykum! Botdan foydalanish uchun tilni tanlang:\n"
            "Здравствуйте! Для использования бота выберите язык:",
            reply_markup=get_language_keyboard()
        )
        await state.set_state(Registration.language)


@router.message(Registration.language, F.text.in_(LANG_MAP.keys()))
async def select_language(message: types.Message, state: FSMContext):
    lang = LANG_MAP[message.text]
    await state.update_data(language=lang)

    if lang == "ru":
        text = "Спасибо! Теперь отправьте ваш номер телефона (нажмите кнопку ниже):"
    elif lang == "uz_cyrl":
        text = "Раҳмат! Энди телефон рақамингизни юборинг (пастдаги тугмани босинг):"
    else:
        text = "Rahmat! Endi telefon raqamingizni yuboring (pastdagi tugmani bosing):"
    await message.answer(text, reply_markup=get_phone_keyboard(lang))
    await state.set_state(Registration.phone_number)


@router.message(Registration.phone_number, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    try:
        normalized_phone = normalize_phone_number(message.contact.phone_number)
    except ValueError:
        normalized_phone = message.contact.phone_number
    await state.update_data(phone_number=normalized_phone)
    data = await state.get_data()
    lang = data.get("language", "uz")

    if lang == "ru":
        text = "Выберите вашу роль:"
    elif lang == "uz_cyrl":
        text = "Ролингизни танланг:"
    else:
        text = "Rolingizni tanlang:"

    await message.answer(text, reply_markup=get_role_keyboard(lang))
    await state.set_state(Registration.role)


@router.message(Registration.role, F.text.in_(ROLE_MAP.keys()))
async def select_role(message: types.Message, state: FSMContext):
    role = ROLE_MAP[message.text]
    data = await state.get_data()
    lang = data.get("language", "uz")
    phone = data.get("phone_number")

    tg_user = message.from_user
    user = await db.get_user(tg_user.id)

    if not user:
        await db.create_user(
            user_id=tg_user.id,
            full_name=tg_user.full_name,
            username=tg_user.username,
            language=lang,
            phone_number=phone,
            role=role
        )
    else:
        await db.update_user_profile_from_tg(
            user_id=tg_user.id,
            full_name=tg_user.full_name,
            username=tg_user.username,
            language=lang,
            phone_number=phone,
            role=role
        )

    if lang == "ru":
        text = (
            f"✅ Вы успешно зарегистрированы, {tg_user.full_name}!\n"
            "Теперь вы можете пользоваться услугами бота."
        )
    elif lang == "uz_cyrl":
        text = (
            f"✅ Рўйхатдан ўтдингиз, {tg_user.full_name}!\n"
            "Энди бот хизматларидан фойдаланишингиз muмкин."
        )
    else:
        text = (
            f"✅ Ro'yxatdan o'tdingiz, {tg_user.full_name}!\n"
            "Endi bot xizmatlaridan foydalanishingiz mumkin."
        )

    # TUZATILDI: Ro'yxatdan o'tish tugaganligi haqida xabar yuborish qo'shildi
    await message.answer(text, reply_markup=types.ReplyKeyboardRemove())  # Eski tugmalarni o'chirish uchun
    await state.clear()


@router.message(Registration.language)
@router.message(Registration.phone_number)
@router.message(Registration.role)
async def skip_registration(message: types.Message):
    """Ro'yxatdan o'tish paytida boshqa narsa yozsa qayta so'rash."""
    await message.answer("Iltimos, ro'yxatdan o'tishni yakunlang (kerakli tugmani bosing).")