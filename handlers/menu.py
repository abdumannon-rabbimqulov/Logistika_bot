from aiogram import Router, types, F
from config.database import db

router = Router()

@router.message(F.text.in_(["👤 Profil", "👤 Мой профиль"]))
async def show_profile(message: types.Message, _):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return

    role_key = "profile_role_user" if user_data['role'] == 'user' else "profile_role_driver"
    role_name = _(role_key)
    
    profile_text = (
        f"<b>{_('profile_title')}</b>\n\n"
        f"{_('profile_name', name=user_data['first_name'])}\n"
        f"{_('profile_role', role=role_name)}\n"
        f"{_('profile_balance', balance=user_data['balance'])}\n"
        f"{_('profile_phone', phone=user_data['phone_number'] or '—')}"
    )
    
    await message.answer(profile_text, parse_mode="HTML")

@router.message(F.text.in_(["ℹ️ Ma'lumot", "ℹ️ Информация"]))
async def show_info(message: types.Message, _):
    await message.answer(_("menu_info_msg"))

@router.message(F.text.in_(["🚛 Buyurtma berish", "🚛 Заказать перевозку", "📦 Mening yuklarim", "📦 Мои грузы", "🚛 Buyurtmalar qidirish", "🚛 Поиск заказов", "📦 Faol buyurtma", "📦 Активный заказ", "🚗 Mening mashinalarim", "🚗 Мои машины"]))
async def under_construction(message: types.Message, _):
    await message.answer(_("under_construction"))
