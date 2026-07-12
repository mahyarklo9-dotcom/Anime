"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), server_default=""),
        sa.Column("title", sa.String(64), server_default="Rookie"),
        sa.Column("xp", sa.Integer(), server_default="0"),
        sa.Column("level", sa.Integer(), server_default="1"),
        sa.Column("wins", sa.Integer(), server_default="0"),
        sa.Column("losses", sa.Integer(), server_default="0"),
        sa.Column("games_played", sa.Integer(), server_default="0"),
        sa.Column("correct_answers", sa.Integer(), server_default="0"),
        sa.Column("wrong_answers", sa.Integer(), server_default="0"),
        sa.Column("best_score", sa.Integer(), server_default="0"),
        sa.Column("is_banned", sa.Boolean(), server_default=sa.false()),
        sa.Column("ban_reason", sa.String(256), nullable=True),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false()),
        sa.Column("language", sa.String(8), server_default="en"),
        sa.Column("notifications_enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), unique=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(256), nullable=False),
        sa.Column("icon", sa.String(8), server_default="🏅"),
    )

    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "achievement_id", sa.Integer(), sa.ForeignKey("achievements.id"), nullable=False
        ),
        sa.Column("earned_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "achievement_id"),
    )

    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "mode",
            sa.Enum("single", "group", "private", "tournament", "daily", "practice", name="gamemode"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "finished", "aborted", name="sessionstatus"),
            server_default="active",
        ),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("host_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("strikes", sa.Integer(), server_default="0"),
        sa.Column("revealed_answer_ids", sa.Text(), server_default=""),
        sa.Column("team_score", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "session_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id", sa.Integer(), sa.ForeignKey("game_sessions.id"), nullable=False
        ),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("correct_answers", sa.Integer(), server_default="0"),
        sa.UniqueConstraint("session_id", "user_id"),
    )

    op.create_table(
        "aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alias_normalized", sa.String(128), nullable=False),
        sa.Column("canonical_answer_normalized", sa.String(128), nullable=False),
        sa.UniqueConstraint("alias_normalized"),
    )

    op.create_table(
        "daily_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("challenge_date", sa.Date(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("challenge_date"),
    )

    op.create_table(
        "daily_challenge_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("challenge_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("completed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "challenge_date"),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.String(1024), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("daily_challenge_completions")
    op.drop_table("daily_challenges")
    op.drop_table("aliases")
    op.drop_table("session_players")
    op.drop_table("game_sessions")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_table("users")
    sa.Enum(name="gamemode").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sessionstatus").drop(op.get_bind(), checkfirst=True)
