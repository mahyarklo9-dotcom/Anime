"""Service computing daily/weekly/monthly/all-time leaderboards."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select

from database import AppSession
from models.app import GameSession, SessionPlayer, User


@dataclass(frozen=True)
class LeaderboardEntry:
    user: User
    period_score: int


class LeaderboardService:
    async def all_time(self, limit: int = 10) -> list[User]:
        async with AppSession() as session:
            stmt = select(User).order_by(User.xp.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def windowed(self, since: datetime, limit: int = 10) -> list[LeaderboardEntry]:
        """Leaderboard ranked by points scored in sessions since ``since``."""
        async with AppSession() as session:
            stmt = (
                select(SessionPlayer.user_id, func.sum(SessionPlayer.score).label("total"))
                .join(GameSession, GameSession.id == SessionPlayer.session_id)
                .where(GameSession.started_at >= since)
                .group_by(SessionPlayer.user_id)
                .order_by(func.sum(SessionPlayer.score).desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.all()

            entries: list[LeaderboardEntry] = []
            for user_id, total in rows:
                user = await session.get(User, user_id)
                if user:
                    entries.append(LeaderboardEntry(user=user, period_score=int(total)))
            return entries

    async def daily(self, limit: int = 10) -> list[LeaderboardEntry]:
        return await self.windowed(datetime.utcnow() - timedelta(days=1), limit)

    async def weekly(self, limit: int = 10) -> list[LeaderboardEntry]:
        return await self.windowed(datetime.utcnow() - timedelta(days=7), limit)

    async def monthly(self, limit: int = 10) -> list[LeaderboardEntry]:
        return await self.windowed(datetime.utcnow() - timedelta(days=30), limit)


leaderboard_service = LeaderboardService()
