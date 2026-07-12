"""
Application configuration.

All runtime configuration is loaded from environment variables (via a .env
file in local development, or real environment variables on Railway). No
secret ever has a hardcoded fallback value that would work in production.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    """Read an environment variable, optionally enforcing that it is set."""
    value = os.getenv(name) or (os.getenv("TOKEN") if name=="BOT_TOKEN" else None) or default
    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and fill it in."
        )
    return value or ""


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    """Immutable application configuration snapshot."""

    # --- Telegram ---
    bot_token: str
    admin_ids: tuple[int, ...]

    # --- Database ---
    questions_db_path: str
    app_db_url: str

    # --- Gameplay ---
    max_strikes: int
    round_timer_seconds: int
    fuzzy_match_threshold: float
    hint_penalty_percent: int

    # --- XP / Scoring ---
    xp_correct_answer: int
    xp_win: int
    xp_daily_bonus: int

    # --- Misc ---
    log_level: str
    environment: str

    @staticmethod
    def load() -> "Config":
        admin_ids_raw = _get_env("ADMIN_IDS", default="")
        admin_ids = tuple(
            int(part.strip())
            for part in admin_ids_raw.split(",")
            if part.strip().isdigit()
        )
        return Config(
            bot_token=_get_env("BOT_TOKEN", required=True),
            admin_ids=admin_ids,
            questions_db_path=_get_env(
                "QUESTIONS_DB_PATH",
                default=str(BASE_DIR / "data" / "anime_family_feud_200.db"),
            ),
            app_db_url=_get_env(
                "APP_DATABASE_URL",
                default=f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'app_state.db'}",
            ),
            max_strikes=_get_int("MAX_STRIKES", 3),
            round_timer_seconds=_get_int("ROUND_TIMER_SECONDS", 60),
            fuzzy_match_threshold=_get_float("FUZZY_MATCH_THRESHOLD", 82.0),
            hint_penalty_percent=_get_int("HINT_PENALTY_PERCENT", 25),
            xp_correct_answer=_get_int("XP_CORRECT_ANSWER", 10),
            xp_win=_get_int("XP_WIN", 50),
            xp_daily_bonus=_get_int("XP_DAILY_BONUS", 100),
            log_level=_get_env("LOG_LEVEL", default="INFO"),
            environment=_get_env("ENVIRONMENT", default="production"),
        )


def setup_logging(level: str) -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quiet down noisy third-party loggers.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


config: Config = Config.load()
