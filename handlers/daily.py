"""Daily Challenge entry point.

v1 ships Single Player and Group Match only (by design, see README). This
handler keeps the button/command working with an honest message instead
of silently failing, and the ``daily_challenges`` / completions tables
already exist so the full mode can be dropped in later without a schema
migration.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.main_menu import main_menu_kb

router = Router(name="daily")

COMING_SOON_TEXT = (
    "🎯 <b>Daily Challenge</b>\n\n"
    "Coming in a future update! For now, jump into a regular round with 🎮 Play — "
    "your progress and XP still count toward your profile."
)


@router.callback_query(F.data == "menu:daily")
async def cb_daily(callback: CallbackQuery) -> None:
    await callback.message.edit_text(COMING_SOON_TEXT, reply_markup=main_menu_kb())
    await callback.answer()
