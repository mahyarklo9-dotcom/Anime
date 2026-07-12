"""Declarative bases for the two databases used by the bot.

Two separate SQLAlchemy "Base" classes are used on purpose:

- ``QuestionsBase`` maps onto the *read-only* trivia database supplied by
  the game designer (``anime_family_feud_200.db``). The bot never writes
  to this database.
- ``AppBase`` maps onto the bot's own state database (users, sessions,
  scores, achievements, etc.), which the bot fully owns and migrates with
  Alembic.
"""
from sqlalchemy.orm import DeclarativeBase


class QuestionsBase(DeclarativeBase):
    """Base class for models mapped to the read-only questions database."""


class AppBase(DeclarativeBase):
    """Base class for models mapped to the bot's own state database."""
