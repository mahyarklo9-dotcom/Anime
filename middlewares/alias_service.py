"""Service for managing the alias -> canonical answer lookup table."""
from __future__ import annotations

import logging

from sqlalchemy import select

from data.seed_aliases import SEED_ALIASES
from database import AppSession
from models.app import Alias
from utils.text import normalize

logger = logging.getLogger(__name__)


class AliasService:
    """Loads and mutates the aliases table, and builds the in-memory lookup
    dict consumed by :class:`services.matching_service.AnswerMatcher`."""

    async def ensure_seeded(self) -> None:
        """Insert the built-in seed aliases if the table is empty.

        Safe to call on every startup; it's a no-op once seeded.
        """
        async with AppSession() as session:
            existing = await session.execute(select(Alias.id).limit(1))
            if existing.first() is not None:
                return

            for alias, canonical in SEED_ALIASES:
                session.add(
                    Alias(
                        alias_normalized=normalize(alias),
                        canonical_answer_normalized=normalize(canonical),
                    )
                )
            await session.commit()
            logger.info("Seeded %d aliases", len(SEED_ALIASES))

    async def add_alias(self, alias: str, canonical_answer: str) -> None:
        async with AppSession() as session:
            session.add(
                Alias(
                    alias_normalized=normalize(alias),
                    canonical_answer_normalized=normalize(canonical_answer),
                )
            )
            await session.commit()

    async def load_lookup(self) -> dict[str, str]:
        """Return the full alias table as a {alias: canonical} dict."""
        async with AppSession() as session:
            result = await session.execute(
                select(Alias.alias_normalized, Alias.canonical_answer_normalized)
            )
            return {alias: canonical for alias, canonical in result.all()}


alias_service = AliasService()
