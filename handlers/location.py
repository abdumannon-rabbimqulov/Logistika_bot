from aiogram import Router, types, F
from config.database import db
from keyboards.reply import get_driver_menu

router = Router()

@router.message(F.text.in_(["🟢 Liniyaga kirish", "🟢 Выйти на линию"]))
async def go_online(message: types.Message, _):
    await db.set_online_status(message.from_user.id, True)
    await message.answer(
        _("go_online_msg"),
        reply_markup=get_driver_menu(_, is_online=True)
    )

@router.message(F.text.in_(["🔴 Liniyadan chiqish", "🔴 Уйти с линии"]))
async def go_offline(message: types.Message, _):
    await db.set_online_status(message.from_user.id, False)
    await message.answer(
        _("go_offline_msg"),
        reply_markup=get_driver_menu(_, is_online=False)
    )

@router.message(F.location)
async def handle_location(message: types.Message):
    user_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    
    # Update location and implicitly set online if not already
    await db.update_location(user_id, lat, lon)
