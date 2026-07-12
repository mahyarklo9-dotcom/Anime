"""
ORM models for the bot's own state database.

This database is fully owned by the bot and evolved via Alembic
migrations (see ``migrations/``). It is intentionally separate from the
supplied trivia database so that the source question data is never at
risk of being modified by application code.
"""
from __future__ import annotations

import enum
from datetime import datetime, date

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import AppBase


class GameMode(str, enum.Enum):
    """Supported game modes.

    Only SINGLE and GROUP are wired up to gameplay in this release; the
    remaining values are reserved so the schema does not need to change
    when those modes are implemented.
    """

    SINGLE = "single"
    GROUP = "group"
    PRIVATE = "private"
    TOURNAMENT = "tournament"
    DAILY = "daily"
    PRACTICE = "practice"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    FINISHED = "finished"
    ABORTED = "aborted"


class User(AppBase):
    """A Telegram user known to the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(64), default="Rookie")

    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)

    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    wrong_answers: Mapped[int] = mapped_column(Integer, default=0)
    best_score: Mapped[int] = mapped_column(Integer, default=0)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    language: Mapped[str] = mapped_column(String(8), default="en")
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    @property
    def accuracy(self) -> float:
        """Correct-answer accuracy as a percentage, 0 if no answers yet."""
        total = self.correct_answers + self.wrong_answers
        if total == 0:
            return 0.0
        return round((self.correct_answers / total) * 100, 1)


class Achievement(AppBase):
    """Catalog of unlockable achievements."""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(256))
    icon: Mapped[str] = mapped_column(String(8), default="🏅")


class UserAchievement(AppBase):
    """Join table: which users unlocked which achievements, and when."""

    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))
    earned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship()


class GameSession(AppBase):
    """A single round/game of Anime Family Feud, single-player or group."""

    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    mode: Mapped[GameMode] = mapped_column(Enum(GameMode))
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE
    )
    question_id: Mapped[int] = mapped_column(Integer)  # FK into questions.db, not enforced
    host_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    strikes: Mapped[int] = mapped_column(Integer, default=0)
    revealed_answer_ids: Mapped[str] = mapped_column(Text, default="")  # CSV of answer ids
    team_score: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    players: Mapped[list["SessionPlayer"]] = relationship(
        back_populates="session", lazy="selectin"
    )


class SessionPlayer(AppBase):
    """A participant in a (typically group) game session and their score in it."""

    __tablename__ = "session_players"
    __table_args__ = (UniqueConstraint("session_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped["GameSession"] = relationship(back_populates="players")
    user: Mapped["User"] = relationship()


class Alias(AppBase):
    """Maps a colloquial alias to the canonical (normalized) answer text.

    Example: alias='aot' -> canonical_answer='attack on titan'
    """

    __tablename__ = "aliases"
    __table_args__ = (UniqueConstraint("alias_normalized"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias_normalized: Mapped[str] = mapped_column(String(128))
    canonical_answer_normalized: Mapped[str] = mapped_column(String(128))


class DailyChallenge(AppBase):
    """Tracks which question was assigned as 'today's' daily challenge."""

    __tablename__ = "daily_challenges"
    __table_args__ = (UniqueConstraint("challenge_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_date: Mapped[date] = mapped_column(Date, default=date.today)
    question_id: Mapped[int] = mapped_column(Integer)


class DailyChallengeCompletion(AppBase):
    """Records that a user completed a given day's daily challenge."""

    __tablename__ = "daily_challenge_completions"
    __table_args__ = (UniqueConstraint("user_id", "challenge_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    challenge_date: Mapped[date] = mapped_column(Date, default=date.today)
    score: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Report(AppBase):
    """A player-submitted bug/content report for admin review."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(String(1024))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
