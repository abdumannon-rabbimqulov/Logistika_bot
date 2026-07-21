from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from config.config import WEBAPP_URL


def get_sender_webapp_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup | None:
    """Sender uchun Mini App (Telegram WebApp) ochish tugmasi.

    Telegram WebApp tugmasi faqat HTTPS URL bilan ishlaydi — aks holda Telegram
    Bot API xabarni butunlay rad etadi (bot handler'i qulab tushmasligi uchun,
    WEBAPP_URL hali https bo'lmagan lokal/dev muhitda shu tugma umuman
    qo'shilmaydi, `None` qaytariladi — chaqiruvchi joyida reply_markup berilmaydi).
    """
    if not WEBAPP_URL.startswith("https://"):
        return None

    if lang == "ru":
        text = "🚀 Отправить груз"
    elif lang == "uz_cyrl":
        text = "🚀 Юк юбориш"
    else:
        text = "🚀 Yuk yuborish"

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text, web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )


def get_language_keyboard():
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

