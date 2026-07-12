"""Handlers for /profile, /stats, /rank, and profile-related callbacks."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards.profile_kb import profile_kb
from models.app import User
from services.achievement_service import achievement_service
from services.user_service import user_service
from utils.formatting import render_profile

router = Router(name="profile")


@router.message(Command("profile"))
async def cmd_profile(message: Message, db_user: User) -> None:
    await message.answer(render_profile(db_user), reply_markup=profile_kb())


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery, db_user: User) -> None:
    await callback.message.edit_text(render_profile(db_user), reply_markup=profile_kb())
    await callback.answer()


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_user: User) -> None:
    text = (
        f"📊 <b>Quick Stats</b>\n\n"
        f"Games: {db_user.games_played}  |  Wins: {db_user.wins}  |  Losses: {db_user.losses}\n"
        f"Accuracy: {db_user.accuracy}%  |  Best Score: {db_user.best_score}\n"
        f"XP: {db_user.xp}  |  Level: {db_user.level}"
    )
    await message.answer(text)


@router.message(Command("rank"))
async def cmd_rank(message: Message, db_user: User) -> None:
    rank = await user_service.rank_of(db_user.id)
    await message.answer(f"🏅 You're ranked <b>#{rank}</b> globally with {db_user.xp} XP.")


@router.callback_query(F.data == "profile:achievements")
async def cb_achievements(callback: CallbackQuery, db_user: User) -> None:
    unlocked = await achievement_service.list_for_user(db_user.id)
    if not unlocked:
        text = "🏅 <b>Achievements</b>\n\nNo achievements yet — play a round to earn your first!"
    else:
        lines = ["🏅 <b>Your Achievements</b>\n"]
        lines += [f"{a.icon} <b>{a.name}</b> — {a.description}" for a in unlocked]
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=profile_kb())
    await callback.answer()
