"""Handlers for /settings and preference toggles."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import AppSession
from keyboards.profile_kb import settings_kb
from models.app import User

router = Router(name="settings")


def _settings_text(user: User) -> str:
    status = "🔔 On" if user.notifications_enabled else "🔕 Off"
    return (
        "⚙ <b>Settings</b>\n\n"
        f"Notifications: <b>{status}</b>\n"
        f"Language: <b>{user.language.upper()}</b>"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, db_user: User) -> None:
    await message.answer(
        _settings_text(db_user), reply_markup=settings_kb(db_user.notifications_enabled)
    )


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery, db_user: User) -> None:
    await callback.message.edit_text(
        _settings_text(db_user), reply_markup=settings_kb(db_user.notifications_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "settings:toggle_notify")
async def cb_toggle_notify(callback: CallbackQuery, db_user: User) -> None:
    async with AppSession() as session:
        user = await session.get(User, db_user.id)
        user.notifications_enabled = not user.notifications_enabled
        await session.commit()
        await session.refresh(user)

    await callback.message.edit_text(
        _settings_text(user), reply_markup=settings_kb(user.notifications_enabled)
    )
    await callback.answer("Preference updated.")
