from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import WHITELIST


class AuthMiddleware(BaseMiddleware):
    """Blocks all users not in the whitelist."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return

        if user.id not in WHITELIST:
            if isinstance(event, (Message, CallbackQuery)):
                target = event.message if isinstance(event, CallbackQuery) else event
                await target.answer(
                    "⛔ Sizga bu botdan foydalanish huquqi yo'q.\n"
                    "Murojaat uchun: @admin"
                )
            return

        # Inject role into handler data
        data["role"] = WHITELIST[user.id]
        return await handler(event, data)
