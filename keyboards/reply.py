from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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

def get_main_menu(_):
    """Returns the main menu keyboard for users."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("main_menu_order")), KeyboardButton(text=_("main_menu_my_loads"))],
            [KeyboardButton(text=_("main_menu_profile")), KeyboardButton(text=_("main_menu_info"))]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_cargo_type_keyboard(_):
    """Returns the cargo type selection keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("cargo_food")), KeyboardButton(text=_("cargo_const"))],
            [KeyboardButton(text=_("cargo_auto")), KeyboardButton(text=_("cargo_electro"))],
            [KeyboardButton(text=_("cargo_other")), KeyboardButton(text=_("btn_back"))]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_confirmation_keyboard(_):
    """Returns the confirmation/cancel keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("btn_confirm")), KeyboardButton(text=_("btn_cancel"))]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_role_keyboard(_):
    """Keyboard for selecting role."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("role_customer")), KeyboardButton(text=_("role_driver"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_driver_menu(_, is_online=False):
    """Driver's main menu."""
    status_text = _("driver_menu_offline") if is_online else _("driver_menu_online")
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=status_text)],
            [KeyboardButton(text=_("driver_menu_search")), KeyboardButton(text=_("driver_menu_active"))],
            [KeyboardButton(text=_("driver_menu_vehicles")), KeyboardButton(text=_("main_menu_profile"))]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_cancel_back_keyboard(_):
    """Keyboard with back and cancel buttons."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("btn_back")), KeyboardButton(text=_("btn_cancel"))]
        ],
        resize_keyboard=True
    )
    return keyboard
