from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.reply import get_main_menu, get_role_keyboard, get_driver_menu, get_language_keyboard
from locales import locales

router = Router()

class StartState(StatesGroup):
    language = State()

@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext, _):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username

    # Find or add user
    user = await db.get_user(user_id)
    
    if not user:
        # First time user - ask for language
        await state.set_state(StartState.language)
        await message.answer(
            f"Salom, {full_name}!\nLogistika botimizga xush kelibsiz.\nIltimos, muloqot tilini tanlang / Пожалуйста, выберите язык:",
            reply_markup=get_language_keyboard()
        )
        # Add to DB with default 'uz' for now
        await db.add_user_to_db(user_id, full_name, username)
    else:
        # Existing user - show menu based on role
        if user['role'] == 'driver':
            await message.answer(_("driver_welcome", full_name=full_name), reply_markup=get_driver_menu(_,))
        elif user['role'] == 'user':
             await message.answer(_("customer_welcome", full_name=full_name), reply_markup=get_main_menu(_))
        else:
            await message.answer(_("select_role"), reply_markup=get_role_keyboard(_))

@router.message(StartState.language, F.text.in_(["🇺🇿 O'zbekcha", "🇷🇺 Русский"]))
async def select_language(message: types.Message, state: FSMContext, _):
    lang_code = "uz" if "O'zbekcha" in message.text else "ru"
    await db.update_user_language(message.from_user.id, lang_code)
    
    # Update translation function for the next message in this handler

    new_gettext = lambda key, **kwargs: locales.get(key, lang_code, **kwargs)
    
    await state.clear()
    await message.answer(new_gettext("select_role"), reply_markup=get_role_keyboard(new_gettext))

@router.message(F.text.in_(["🙋‍♂️ Yuk egasi (Mijoz)", "🙋‍♂️ Грузовладелец (Клиент)"]))
async def set_customer_role(message: types.Message, _):
    await db.update_user_role(message.from_user.id, 'user')
    await message.answer(_("customer_registered"), reply_markup=get_main_menu(_))
