from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from db import db
from locales import locales

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        
        if user:
            # Try to get user from DB
            db_user = await db.get_user(user.id)
            
            if db_user:
                lang_code = db_user.get("language_code", "uz")
            else:
                # Default to uz for new users
                lang_code = "uz"
            
            # Inject translation function and language code
            data["lang"] = lang_code
            data["_"] = lambda key, **kwargs: locales.get(key, lang_code, **kwargs)
        
        return await handler(event, data)
