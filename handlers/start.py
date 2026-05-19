from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.reply import (
    get_language_keyboard,
    get_phone_keyboard,
    get_role_keyboard,
)
from users.models import UserRole
import database as db

router = Router()

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

    user = await db.get_user(message.from_user.id)

    if user and user.phone_number:


        if user.language == "ru":
            greet = "Здравствуйте"
            help_text = "Чем могу помочь?"
        elif user.language == "uz_cyrl":
            greet = "Ассалому алайкум"
            help_text = "Сизга қандай ёрдам бера оламан?"
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
    await state.update_data(phone_number=message.contact.phone_number)
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
            "Энди бот хизматларидан фойдаланишингиз мумкин."
        )
    else:
        text = (
            f"✅ Ro'yxatdan o'tdingiz, {tg_user.full_name}!\n"
            "Endi bot xizmatlaridan foydalanishingiz mumkin."
        )
    await state.clear()


@router.message(Registration.language)
@router.message(Registration.phone_number)
@router.message(Registration.role)
async def skip_registration(message: types.Message):
    """Ro'yxatdan o'tish paytida boshqa narsa yozsa qayta so'rash."""
    await message.answer("Iltimos, ro'yxatdan o'tishni yakunlang (kerakli tugmani bosing).")
