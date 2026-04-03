import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class ShadowLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            msg_text = event.text or "[Media/Other]"
            logging.info(f"📥 [MESSAGE] From: {user.full_name} (@{user.username}, ID: {user.id}) | Content: {msg_text}")
        
        result = await handler(event, data)
        return result
