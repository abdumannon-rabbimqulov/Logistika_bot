from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from database.db import db
from locales import locales

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        
        # Default language
        lang_code = "uz"
        
        if user:
            # Try to get user from DB
            db_user = await db.get_user(user.id)
            
            if db_user:
                # User model has 'language' field
                lang_code = db_user.language or "uz"
            else:
                # Default to Telegram's language if supported
                tg_lang = user.language_code
                if tg_lang in ['uz', 'ru']:
                    lang_code = tg_lang
            
            # Inject translation function and language code
            data["lang"] = lang_code
            data["_"] = lambda key, **kwargs: locales.get(key, lang_code, **kwargs)
        
        return await handler(event, data)
