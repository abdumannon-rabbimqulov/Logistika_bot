from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def get_language_keyboard():
    """Keyboard for selecting language."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇺🇿 Ўзбекча")],
            [KeyboardButton(text="🇷🇺 Русский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_phone_keyboard(lang: str = "uz"):
    """Keyboard for requesting phone number."""
    if lang == "ru":
        text = "📞 Отправить номер телефона"
    elif lang == "uz_cyrl":
        text = "📞 Телефон рақамини юбориш"
    else:
        text = "📞 Telefon raqamini yuborish"
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text, request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_role_keyboard(lang: str = "uz"):
    """Keyboard for selecting user role."""
    if lang == "ru":
        sender = "📦 Отправитель груза"
        driver = "🚛 Водитель"
    elif lang == "uz_cyrl":
        sender = "📦 Юк берувчи"
        driver = "🚛 Ҳайдовчи"
    else:
        sender = "📦 Yuk beruvchi"
        driver = "🚛 Haydovchi"
        
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=sender), KeyboardButton(text=driver)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

