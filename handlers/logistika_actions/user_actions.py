from ai.db import db
import logging

async def get_profile_action(user_id: int):
    """
    Returns user profile information.
    """
    try:
        user = await db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "Foydalanuvchi ma'lumotlari topilmadi."}
            
        return {
            "status": "success",
            "profile": {
                "name": user.first_name,
                "role": user.role,
                "balance": float(user.balance),
                "phone": user.phone_number or "Kiritilmagan"
            }
        }
    except Exception as e:
        logging.error(f"Error in get_profile_action: {e}")
        return {"status": "error", "message": str(e)}

async def get_help_action():
    """
    Returns general information about the bot and available services.
    """
    return {
        "status": "success",
        "message": (
            "Men Logistika AI yordamchisiman. Men orqali quyidagilarni qilishingiz mumkin:\n"
            "- Yuk yuborish uchun buyurtma yaratish\n"
            "- Buyurtmalaringizni ko'rish va bekor qilish\n"
            "- Profilingizni ko'rish\n"
            "- Agar haydovchi bo'lsangiz, buyurtmalar qidirish va holatingizni o'zgartirish\n\n"
            "Savolingiz bormi?"
        )
    }
