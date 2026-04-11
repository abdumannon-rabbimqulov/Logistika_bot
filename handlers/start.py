from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from database.db import db
from keyboards.reply import get_language_keyboard, get_role_keyboard, get_main_menu, get_driver_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, _):
    await state.clear()
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        # New user
        await message.answer("Xush kelibsiz! Tilni tanlang / Добро пожаловать! Выберите язык:", reply_markup=get_language_keyboard())
    else:
        # Existing user
        if user.role == 'driver':
            await message.answer(_("welcome"), reply_markup=get_driver_menu(_, is_online=False))
        else:
            await message.answer(_("welcome"), reply_markup=get_main_menu(_))

@router.message(F.text.in_(["🇺🇿 O'zbekcha", "🇷🇺 Русский"]))
async def select_language(message: types.Message, _):
    # This usually triggers role selection next
    await message.answer(_("select_role"), reply_markup=get_role_keyboard(_))

@router.message(F.text.in_(["👤 Mijoz", "👤 Клиент"]))
async def select_customer(message: types.Message, _):
    await db.update_user_role(message.from_user.id, 'user')
    await message.answer(_("welcome"), reply_markup=get_main_menu(_))
