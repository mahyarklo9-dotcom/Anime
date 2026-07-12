"""Service layer for user accounts, profiles, and stat/XP updates."""
from __future__ import annotations

from sqlalchemy import select

from database import AppSession
from models.app import User
from utils.leveling import level_for_xp


class UserService:
    """Encapsulates all reads/writes to the ``users`` table."""

    async def get_or_create(
        self, telegram_id: int, username: str | None, first_name: str
    ) -> User:
        async with AppSession() as session:
            user = await session.get(User, telegram_id)
            if user is None:
                user = User(
                    id=telegram_id,
                    username=username,
                    first_name=first_name or "Player",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                return user

            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                await session.commit()
                await session.refresh(user)
            return user

    async def get(self, telegram_id: int) -> User | None:
        async with AppSession() as session:
            return await session.get(User, telegram_id)

    async def is_banned(self, telegram_id: int) -> bool:
        user = await self.get(telegram_id)
        return bool(user and user.is_banned)

    async def set_banned(self, telegram_id: int, banned: bool, reason: str | None = None) -> None:
        async with AppSession() as session:
            user = await session.get(User, telegram_id)
            if user:
                user.is_banned = banned
                user.ban_reason = reason
                await session.commit()

    async def award_xp(self, telegram_id: int, amount: int) -> tuple[int, bool]:
        """Add XP to a user, recompute their level, and report level-ups.

        Returns:
            (new_level, leveled_up)
        """
        async with AppSession() as session:
            user = await session.get(User, telegram_id)
            if user is None:
                return 1, False
            old_level = user.level
            user.xp += amount
            user.level = level_for_xp(user.xp)
            await session.commit()
            return user.level, user.level > old_level

    async def record_answer(self, telegram_id: int, correct: bool) -> None:
        async with AppSession() as session:
            user = await session.get(User, telegram_id)
            if user is None:
                return
            if correct:
                user.correct_answers += 1
            else:
                user.wrong_answers += 1
            await session.commit()

    async def record_game_result(
        self, telegram_id: int, won: bool, final_score: int
    ) -> None:
        async with AppSession() as session:
            user = await session.get(User, telegram_id)
            if user is None:
                return
            user.games_played += 1
            if won:
                user.wins += 1
            else:
                user.losses += 1
            user.best_score = max(user.best_score, final_score)
            await session.commit()

    async def top_players(self, limit: int = 10) -> list[User]:
        async with AppSession() as session:
            stmt = select(User).order_by(User.xp.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def rank_of(self, telegram_id: int) -> int | None:
        """1-indexed global XP rank of a user, or None if they don't exist."""
        from sqlalchemy import func as sa_func

        async with AppSession() as session:
            user = await session.get(User, telegram_id)
            if user is None:
                return None
            stmt = select(sa_func.count(User.id)).where(User.xp > user.xp)
            result = await session.execute(stmt)
            higher = result.scalar_one()
            return higher + 1


user_service = UserService()
