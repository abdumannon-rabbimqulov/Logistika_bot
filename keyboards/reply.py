from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def get_language_keyboard():
    """Keyboard for selecting language."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_phone_keyboard(lang: str = "uz"):
    """Keyboard for requesting phone number."""
    text = "📞 Telefon raqamini yuborish" if lang == "uz" else "📞 Отправить номер телефона"
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text, request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

