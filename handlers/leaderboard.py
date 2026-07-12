"""Handlers for /top and the leaderboard tabs (daily/weekly/monthly/all-time)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards.profile_kb import leaderboard_kb
from models.app import User
from services.leaderboard_service import leaderboard_service

router = Router(name="leaderboard")

MEDALS = ["🥇", "🥈", "🥉"]


def _render_alltime(users: list[User]) -> str:
    if not users:
        return "🏆 <b>All-Time Leaderboard</b>\n\nNo players yet — be the first!"
    lines = ["🏆 <b>All-Time Leaderboard</b>\n"]
    for i, u in enumerate(users):
        prefix = MEDALS[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} {u.first_name} — {u.xp} XP (Lv. {u.level})")
    return "\n".join(lines)


def _render_windowed(title: str, entries) -> str:
    if not entries:
        return f"🏆 <b>{title} Leaderboard</b>\n\nNo games played in this period yet."
    lines = [f"🏆 <b>{title} Leaderboard</b>\n"]
    for i, entry in enumerate(entries):
        prefix = MEDALS[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} {entry.user.first_name} — {entry.period_score} pts")
    return "\n".join(lines)


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    users = await leaderboard_service.all_time()
    await message.answer(_render_alltime(users), reply_markup=leaderboard_kb("alltime"))


@router.callback_query(F.data == "menu:leaderboard")
async def cb_leaderboard_home(callback: CallbackQuery) -> None:
    users = await leaderboard_service.all_time()
    await callback.message.edit_text(_render_alltime(users), reply_markup=leaderboard_kb("alltime"))
    await callback.answer()


@router.callback_query(F.data.startswith("leaderboard:"))
async def cb_leaderboard_tab(callback: CallbackQuery) -> None:
    tab = callback.data.split(":", 1)[1]

    if tab == "alltime":
        users = await leaderboard_service.all_time()
        text = _render_alltime(users)
    elif tab == "daily":
        text = _render_windowed("Daily", await leaderboard_service.daily())
    elif tab == "weekly":
        text = _render_windowed("Weekly", await leaderboard_service.weekly())
    elif tab == "monthly":
        text = _render_windowed("Monthly", await leaderboard_service.monthly())
    else:
        text = "Unknown leaderboard tab."

    await callback.message.edit_text(text, reply_markup=leaderboard_kb(tab))
    await callback.answer()
