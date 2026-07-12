"""Miscellaneous commands: /about and /report."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import AppSession
from models.app import Report, User

router = Router(name="misc")

ABOUT_TEXT = (
    "🎌 <b>Anime Family Feud</b>\n\n"
    "A Family-Feud-style trivia game for anime fans, built with aiogram 3 "
    "and a fuzzy-matching answer engine so you don't need to type answers "
    "perfectly to score.\n\n"
    "Have feedback or found a wrong answer? Use /report."
)


class ReportForm(StatesGroup):
    waiting_for_message = State()


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✖ Cancel", callback_data="menu:home")]]
    )


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext) -> None:
    await state.set_state(ReportForm.waiting_for_message)
    await message.answer(
        "📝 What would you like to report? Send a message describing the issue "
        "(e.g. a wrong answer, a bug, or a suggestion).",
        reply_markup=_cancel_kb(),
    )


@router.message(ReportForm.waiting_for_message)
async def process_report(message: Message, state: FSMContext, db_user: User) -> None:
    await state.clear()
    async with AppSession() as session:
        session.add(Report(user_id=db_user.id, message=message.text or ""))
        await session.commit()
    await message.answer("✅ Thanks! Your report was sent to the team.")
