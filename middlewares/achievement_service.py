"""Service for the achievement catalog and unlock evaluation."""
from __future__ import annotations

import logging

from sqlalchemy import select

from database import AppSession
from models.app import Achievement, User, UserAchievement

logger = logging.getLogger(__name__)

# (code, name, description, icon)
CATALOG: list[tuple[str, str, str, str]] = [
    ("first_win", "First Win", "Win your very first game.", "🥇"),
    ("wins_10", "10 Wins", "Win 10 games.", "🏆"),
    ("wins_50", "50 Wins", "Win 50 games.", "🎖️"),
    ("wins_100", "100 Wins", "Win 100 games.", "👑"),
    ("perfect_round", "Perfect Round", "Reveal every answer with zero strikes.", "💯"),
    ("anime_master", "Anime Master", "Reach level 25.", "🎌"),
    ("otaku", "Otaku", "Answer 500 questions correctly.", "📺"),
    ("legend", "Legend", "Reach level 50.", "🌟"),
    ("speed_runner", "Speed Runner", "Win a round in under 20 seconds.", "⚡"),
    ("no_strike", "No Strike", "Win 5 games in a row without a single strike.", "🛡️"),
]


class AchievementService:
    async def ensure_seeded(self) -> None:
        async with AppSession() as session:
            existing = await session.execute(select(Achievement.id).limit(1))
            if existing.first() is not None:
                return
            for code, name, description, icon in CATALOG:
                session.add(
                    Achievement(code=code, name=name, description=description, icon=icon)
                )
            await session.commit()
            logger.info("Seeded %d achievements", len(CATALOG))

    async def unlock(self, telegram_id: int, code: str) -> Achievement | None:
        """Grant an achievement to a user if they don't already have it.

        Returns the Achievement if it was newly granted, else None.
        """
        async with AppSession() as session:
            achievement = await session.scalar(
                select(Achievement).where(Achievement.code == code)
            )
            if achievement is None:
                logger.warning("Unknown achievement code: %s", code)
                return None

            already = await session.scalar(
                select(UserAchievement).where(
                    UserAchievement.user_id == telegram_id,
                    UserAchievement.achievement_id == achievement.id,
                )
            )
            if already is not None:
                return None

            session.add(
                UserAchievement(user_id=telegram_id, achievement_id=achievement.id)
            )
            await session.commit()
            return achievement

    async def list_for_user(self, telegram_id: int) -> list[Achievement]:
        async with AppSession() as session:
            stmt = (
                select(Achievement)
                .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
                .where(UserAchievement.user_id == telegram_id)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def evaluate_post_game(self, user: User, perfect_round: bool) -> list[Achievement]:
        """Check win/level/accuracy-based achievements after a game ends.

        Called with an already-updated User row (wins/level reflect the
        game that just finished).
        """
        newly_unlocked: list[Achievement] = []

        candidates: list[str] = []
        if user.wins >= 1:
            candidates.append("first_win")
        if user.wins >= 10:
            candidates.append("wins_10")
        if user.wins >= 50:
            candidates.append("wins_50")
        if user.wins >= 100:
            candidates.append("wins_100")
        if user.level >= 25:
            candidates.append("anime_master")
        if user.level >= 50:
            candidates.append("legend")
        if user.correct_answers >= 500:
            candidates.append("otaku")
        if perfect_round:
            candidates.append("perfect_round")

        for code in candidates:
            unlocked = await self.unlock(user.id, code)
            if unlocked:
                newly_unlocked.append(unlocked)
        return newly_unlocked


achievement_service = AchievementService()
