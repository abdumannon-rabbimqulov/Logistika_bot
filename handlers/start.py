from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from users.models import UserRole

from keyboards.reply import (
    get_language_keyboard,
    get_phone_keyboard,
    get_role_keyboard,
    get_sender_webapp_keyboard,
)
from users.models import UserRole
import database as db
from config.config import ADMIN_IDS
from utils.validation import normalize_phone_number

router = Router()


def resolve_role(telegram_id: int, chosen_role: UserRole) -> UserRole:
    """Bazaga yozishdan oldin yakuniy rolni aniqlaydi.

    Admin huquqi foydalanuvchi tanlovi bilan emas, `.env` dagi `ADMIN` ro'yxati bilan
    beriladi. Tekshiruv ATAYLAB shu yerda — ya'ni ro'yxatdan o'tish to'liq tugab,
    telefon raqami olingandan keyin. Ilgari `/start` da tekshirilib, admin registratsiya
    oqimini butunlay chetlab o'tardi va bazada `phone_number` NULL bo'lib qolardi.
    """
    if telegram_id in ADMIN_IDS:
        return UserRole.ADMIN
    return chosen_role


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

    # DIQQAT: bu yerda admin uchun ALOHIDA yo'l YO'Q. Admin ham hamma qatori tilni
    # tanlaydi va telefon raqamini yuboradi; `role="admin"` esa faqat oxirida,
    # `select_role` ichida `resolve_role()` orqali beriladi.

    if user and user.phone_number:
        # Ro'yxatdan o'tgan foydalanuvchi keyinchalik `ADMIN` ro'yxatiga qo'shilgan
        # bo'lishi mumkin — qayta ro'yxatdan o'tkazmasdan rolini moslaymiz. Telefon
        # raqami allaqachon bazada, ya'ni talab buzilmaydi.
        if tg_id in ADMIN_IDS and user.role != UserRole.ADMIN:
            await db.update_user_profile_from_tg(
                user_id=tg_id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                language=user.language,
                phone_number=user.phone_number,
                role=UserRole.ADMIN,
            )
            user = await db.get_user(tg_id)

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
        webapp_kb = get_sender_webapp_keyboard(user.language) if user.role == UserRole.SENDER else None
        await message.answer(f"{greet}, {message.from_user.full_name}!\n{help_text}", reply_markup=webapp_kb)
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
    chosen_role = ROLE_MAP[message.text]
    data = await state.get_data()
    lang = data.get("language", "uz")
    phone = data.get("phone_number")

    tg_user = message.from_user

    # Telefon raqamisiz saqlamaymiz — aks holda bazada NULL qolib ketadi. Bunday holat
    # (masalan bot qayta ishga tushib, FSM ma'lumoti yo'qolsa) foydalanuvchini shu
    # qadamga qaytaradi, FSM esa TOZALANMAYDI.
    if not phone:
        if lang == "ru":
            text = "Сначала отправьте номер телефона (нажмите кнопку ниже):"
        elif lang == "uz_cyrl":
            text = "Аввал телефон рақамингизни юборинг (пастдаги тугмани босинг):"
        else:
            text = "Avval telefon raqamingizni yuboring (pastdagi tugmani bosing):"
        await message.answer(text, reply_markup=get_phone_keyboard(lang))
        await state.set_state(Registration.phone_number)
        return

    # Yakuniy rol: `.env` dagi ADMIN ro'yxatida bo'lsa — admin, aks holda tanlangani.
    role = resolve_role(tg_user.id, chosen_role)

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

    # FSM AYNAN shu yerda tozalanadi — ro'yxatdan o'tish tugab, telefon raqami bazaga
    # yozilgandan keyin. Yuqoridagi erta `return` yo'llarida tozalanmaydi.
    await state.clear()

    if role == UserRole.ADMIN:
        await message.answer(
            f"✅ Ro'yxatdan o'tdingiz, {tg_user.full_name}!\n"
            "Siz admin sifatida aniqlandingiz — boshqaruv paneli huquqlari ochildi.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return

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

    webapp_kb = get_sender_webapp_keyboard(lang) if role == UserRole.SENDER else None
    await message.answer(text, reply_markup=webapp_kb or types.ReplyKeyboardRemove())


@router.message(Registration.language)
@router.message(Registration.phone_number)
@router.message(Registration.role)
async def skip_registration(message: types.Message):
    """Ro'yxatdan o'tish paytida boshqa narsa yozsa qayta so'rash."""
    await message.answer("Iltimos, ro'yxatdan o'tishni yakunlang (kerakli tugmani bosing).")