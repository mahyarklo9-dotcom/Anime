"""Rendering helpers that turn game/domain state into Telegram message text."""
from __future__ import annotations

from game import RoundState
from models.app import User
from utils.leveling import xp_progress

STRIKE_EMOJI = "❌"
EMPTY_STRIKE_EMOJI = "▫️"


def render_board(state: RoundState) -> str:
    """Render the current board state as a Family-Feud-style message."""
    lines = [
        f"🎌 <b>{state.question.category}</b>",
        f"❓ <i>{state.question.question}</i>",
        "",
    ]
    for i, answer in enumerate(state.board, start=1):
        if answer.revealed:
            lines.append(f"{i}. <b>{answer.text.title()}</b> — {answer.points} pts")
        else:
            lines.append(f"{i}. <code>?????????</code>")

    strikes_display = (
        STRIKE_EMOJI * state.strikes + EMPTY_STRIKE_EMOJI * (state.max_strikes - state.strikes)
    )
    team_score = sum(state.player_scores.values())

    lines += [
        "",
        f"Strikes: {strikes_display}",
        f"Score: <b>{team_score}</b> pts",
        f"⏱ {state.elapsed_seconds()}s elapsed",
    ]
    return "\n".join(lines)


def render_profile(user: User) -> str:
    level, into_level, needed = xp_progress(user.xp)
    bar_len = 12
    filled = int(bar_len * (into_level / needed)) if needed else bar_len
    bar = "█" * filled + "░" * (bar_len - filled)

    return (
        f"👤 <b>{user.first_name}</b>  ·  <i>{user.title}</i>\n\n"
        f"🎚 Level {level}  [{bar}] {into_level}/{needed} XP\n"
        f"⭐ Total XP: <b>{user.xp}</b>\n\n"
        f"🏆 Wins: <b>{user.wins}</b>   💀 Losses: <b>{user.losses}</b>\n"
        f"🎮 Games Played: <b>{user.games_played}</b>\n"
        f"🎯 Accuracy: <b>{user.accuracy}%</b>\n"
        f"📈 Best Score: <b>{user.best_score}</b>"
    )


def render_leaderboard(users: list[User], you: User | None = None) -> str:
    if not users:
        return "No players on the leaderboard yet — be the first!"

    medal = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Leaderboard</b>\n"]
    for i, u in enumerate(users):
        prefix = medal[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} {u.first_name} — {u.xp} XP (Lv. {u.level})")

    if you and you.id not in {u.id for u in users}:
        lines.append(f"\n...\n{you.first_name} (you) — {you.xp} XP")

    return "\n".join(lines)
