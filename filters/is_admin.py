"""Filter that restricts a handler to configured bot admins."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import config


class IsAdmin(BaseFilter):
    """Matches only if the sender's Telegram user id is in ADMIN_IDS."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if user is None:
            return False
        return user.id in config.admin_ids
