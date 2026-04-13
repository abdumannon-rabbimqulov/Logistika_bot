from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards.reply import get_language_keyboard, get_role_keyboard, get_main_menu, get_driver_menu
import database as db

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, _):
    await state.clear()
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if not user:
        # Yangi foydalanuvchi — til tanlash
        await message.answer(
            "Xush kelibsiz! Tilni tanlang / Добро пожаловать! Выберите язык:",
            reply_markup=get_language_keyboard()
        )
    else:
        # Mavjud foydalanuvchi — roliga qarab menyu
        if user.role == 'driver':
            await message.answer(_("welcome"), reply_markup=get_driver_menu(_, is_online=False))
        else:
            await message.answer(_("welcome"), reply_markup=get_main_menu(_))


@router.message(F.text.in_(["🇺🇿 O'zbekcha", "🇷🇺 Русский"]))
async def select_language(message: types.Message, _):
    await message.answer(_("select_role"), reply_markup=get_role_keyboard(_))
