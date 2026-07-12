"""Handlers for /start and the main menu navigation callbacks."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import main_menu_kb
from models.app import User

router = Router(name="start")

WELCOME_TEXT = (
    "🎌 <b>Welcome to Anime Family Feud!</b>\n\n"
    "Guess the top answers on the board before you run out of strikes. "
    "Play solo, challenge your group chat, or take on the Daily Challenge.\n\n"
    "Pick an option below to get started 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:home")
async def cb_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb())
    await callback.answer()
