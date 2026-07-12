"""
Answer matching service.

Implements four progressively more forgiving layers of matching, in
order, stopping at the first that succeeds:

    1. Exact match          - byte-for-byte identical strings.
    2. Normalized match     - case/whitespace/symbol/unicode-insensitive.
    3. Alias match          - known shorthand -> canonical answer lookup.
    4. Fuzzy match          - RapidFuzz similarity above a configurable
                               threshold.

A fifth, optional layer (:class:`SemanticMatcher`) is defined as an
interface only. It is wired into :class:`AnswerMatcher` but is a no-op
until an LLM API key is configured, so the architecture supports
"smart" matching (e.g. "pirate with a straw hat" -> "Luffy") without any
code changes once that key is supplied.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from rapidfuzz import fuzz

from utils.text import normalize

logger = logging.getLogger(__name__)


class MatchLayer:
    """Enum-like constants identifying which layer produced a match."""

    EXACT = "exact"
    NORMALIZED = "normalized"
    ALIAS = "alias"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    NONE = "none"


@dataclass(frozen=True)
class MatchResult:
    """Outcome of attempting to match a player's guess to a board answer."""

    matched: bool
    answer_id: int | None = None
    answer_text: str | None = None
    points: int = 0
    layer: str = MatchLayer.NONE
    score: float = 0.0  # similarity score 0-100, 100 for exact/alias matches


@dataclass(frozen=True)
class BoardAnswer:
    """A single answer slot on the board, as seen by the matcher."""

    id: int
    text: str
    points: int
    revealed: bool = False


class SemanticMatcher(Protocol):
    """Interface for a future LLM-backed matching layer.

    Implement this against any provider (Anthropic, OpenAI, a local
    model, ...) and pass an instance into :class:`AnswerMatcher` to
    enable layer 5 with zero changes elsewhere in the codebase. Until
    then, :class:`NullSemanticMatcher` keeps this layer inert.

    Example future implementation would send the guess plus the list of
    unrevealed board answers to an LLM and ask it to pick the closest
    conceptual match, e.g. "pirate with a straw hat" -> "Luffy",
    "orange ninja" -> "Naruto", "strongest sorcerer" -> "Gojo".
    """

    async def match(self, guess: str, candidates: list[BoardAnswer]) -> MatchResult:
        ...


class NullSemanticMatcher:
    """Default no-op semantic matcher used when no LLM key is configured."""

    async def match(self, guess: str, candidates: list[BoardAnswer]) -> MatchResult:
        return MatchResult(matched=False, layer=MatchLayer.NONE)


class AnswerMatcher:
    """Matches a raw player guess against the current board's answers."""

    def __init__(
        self,
        alias_lookup: dict[str, str] | None = None,
        fuzzy_threshold: float = 82.0,
        semantic_matcher: SemanticMatcher | None = None,
    ) -> None:
        """
        Args:
            alias_lookup: mapping of normalized alias -> normalized
                canonical answer text, typically loaded from the
                ``aliases`` table at startup / per-request.
            fuzzy_threshold: minimum RapidFuzz token_sort_ratio (0-100)
                required to accept a fuzzy match.
            semantic_matcher: optional pluggable LLM-backed layer 5.
        """
        self._alias_lookup = alias_lookup or {}
        self._fuzzy_threshold = fuzzy_threshold
        self._semantic_matcher = semantic_matcher or NullSemanticMatcher()

    async def match(self, guess: str, candidates: list[BoardAnswer]) -> MatchResult:
        """Attempt to match ``guess`` against unrevealed ``candidates``.

        Layers are tried in order of strictness; the first hit wins.
        """
        unrevealed = [c for c in candidates if not c.revealed]
        if not guess.strip() or not unrevealed:
            return MatchResult(matched=False)

        exact_hit = self._exact(guess, unrevealed)
        if exact_hit:
            return exact_hit

        normalized_hit = self._normalized(guess, unrevealed)
        if normalized_hit:
            return normalized_hit

        alias_hit = self._alias(guess, unrevealed)
        if alias_hit:
            return alias_hit

        fuzzy_hit = self._fuzzy(guess, unrevealed)
        if fuzzy_hit:
            return fuzzy_hit

        semantic_hit = await self._semantic_matcher.match(guess, unrevealed)
        if semantic_hit.matched:
            return semantic_hit

        return MatchResult(matched=False)

    # -- individual layers -------------------------------------------------

    @staticmethod
    def _exact(guess: str, candidates: list[BoardAnswer]) -> MatchResult | None:
        for candidate in candidates:
            if guess == candidate.text:
                return MatchResult(
                    matched=True,
                    answer_id=candidate.id,
                    answer_text=candidate.text,
                    points=candidate.points,
                    layer=MatchLayer.EXACT,
                    score=100.0,
                )
        return None

    @staticmethod
    def _normalized(guess: str, candidates: list[BoardAnswer]) -> MatchResult | None:
        guess_norm = normalize(guess)
        if not guess_norm:
            return None
        for candidate in candidates:
            if guess_norm == normalize(candidate.text):
                return MatchResult(
                    matched=True,
                    answer_id=candidate.id,
                    answer_text=candidate.text,
                    points=candidate.points,
                    layer=MatchLayer.NORMALIZED,
                    score=100.0,
                )
        return None

    def _alias(self, guess: str, candidates: list[BoardAnswer]) -> MatchResult | None:
        guess_norm = normalize(guess)
        canonical = self._alias_lookup.get(guess_norm)
        if not canonical:
            return None
        for candidate in candidates:
            if normalize(candidate.text) == canonical:
                return MatchResult(
                    matched=True,
                    answer_id=candidate.id,
                    answer_text=candidate.text,
                    points=candidate.points,
                    layer=MatchLayer.ALIAS,
                    score=100.0,
                )
        return None

    def _fuzzy(self, guess: str, candidates: list[BoardAnswer]) -> MatchResult | None:
        guess_norm = normalize(guess)
        if not guess_norm:
            return None

        best_candidate: BoardAnswer | None = None
        best_score = 0.0
        for candidate in candidates:
            score = fuzz.token_sort_ratio(guess_norm, normalize(candidate.text))
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate and best_score >= self._fuzzy_threshold:
            return MatchResult(
                matched=True,
                answer_id=best_candidate.id,
                answer_text=best_candidate.text,
                points=best_candidate.points,
                layer=MatchLayer.FUZZY,
                score=best_score,
            )
        return None
