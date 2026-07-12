"""
Core game engine.

Owns the in-memory state of currently active rounds (one per chat) and
orchestrates guess submission, scoring, hints, strikes, and round
completion -- including persisting results and awarding XP/achievements.

Kept deliberately free of any Telegram/aiogram imports so it can be unit
tested in isolation and, in principle, reused by a different frontend.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from config import config
from database import AppSession
from models.app import GameMode, GameSession, SessionPlayer
from models.questions import Answer, Question
from services.achievement_service import achievement_service
from services.alias_service import alias_service
from services.matching_service import AnswerMatcher, BoardAnswer, MatchResult
from services.question_service import question_service
from services.user_service import user_service

logger = logging.getLogger(__name__)


class GuessOutcome(str, Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    ALREADY_REVEALED = "already_revealed"
    ROUND_OVER = "round_over"
    NO_ACTIVE_ROUND = "no_active_round"
    BANNED = "banned"


@dataclass
class GuessResult:
    outcome: GuessOutcome
    match: MatchResult | None = None
    strikes: int = 0
    max_strikes: int = 0
    round_finished: bool = False
    won: bool = False


@dataclass
class RoundState:
    """In-memory state for one active round."""

    chat_id: int
    mode: GameMode
    host_id: int
    question: Question
    board: list[BoardAnswer]
    session_id: int
    max_strikes: int
    strikes: int = 0
    player_scores: dict[int, int] = field(default_factory=dict)
    player_correct: dict[int, int] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    hints_used: int = 0
    finished: bool = False

    @property
    def remaining(self) -> list[BoardAnswer]:
        return [a for a in self.board if not a.revealed]

    @property
    def is_cleared(self) -> bool:
        return all(a.revealed for a in self.board)

    def elapsed_seconds(self) -> int:
        return int(time.time() - self.started_at)


class GameEngine:
    """Coordinates active rounds across all chats."""

    def __init__(self) -> None:
        self._rounds: dict[int, RoundState] = {}
        self._alias_lookup_cache: dict[str, str] = {}

    # -- setup ---------------------------------------------------------

    async def refresh_alias_cache(self) -> None:
        self._alias_lookup_cache = await alias_service.load_lookup()

    def _build_matcher(self) -> AnswerMatcher:
        return AnswerMatcher(
            alias_lookup=self._alias_lookup_cache,
            fuzzy_threshold=config.fuzzy_match_threshold,
        )

    # -- round lifecycle -------------------------------------------------

    def has_active_round(self, chat_id: int) -> bool:
        return chat_id in self._rounds and not self._rounds[chat_id].finished

    def get_round(self, chat_id: int) -> RoundState | None:
        return self._rounds.get(chat_id)

    async def start_round(
        self, chat_id: int, host_id: int, mode: GameMode, category: str | None = None
    ) -> RoundState:
        """Start a new round in the given chat, replacing any prior one."""
        question = await question_service.get_random_question(category)
        if question is None:
            raise RuntimeError("No questions available in the database.")

        answers: list[Answer] = await question_service.get_answers(question.id)
        board = [
            BoardAnswer(id=a.id, text=a.answer, points=a.points, revealed=False)
            for a in answers
        ]

        async with AppSession() as session:
            db_session = GameSession(
                chat_id=chat_id,
                mode=mode,
                question_id=question.id,
                host_user_id=host_id,
            )
            session.add(db_session)
            await session.commit()
            await session.refresh(db_session)
            session_id = db_session.id

        state = RoundState(
            chat_id=chat_id,
            mode=mode,
            host_id=host_id,
            question=question,
            board=board,
            session_id=session_id,
            max_strikes=config.max_strikes,
        )
        self._rounds[chat_id] = state
        return state

    async def submit_guess(
        self, chat_id: int, user_id: int, guess: str
    ) -> GuessResult:
        state = self._rounds.get(chat_id)
        if state is None or state.finished:
            return GuessResult(outcome=GuessOutcome.NO_ACTIVE_ROUND)

        if await user_service.is_banned(user_id):
            return GuessResult(outcome=GuessOutcome.BANNED)

        matcher = self._build_matcher()
        result = await matcher.match(guess, state.board)

        if not result.matched:
            state.strikes += 1
            if state.strikes >= state.max_strikes:
                await self._finish_round(state, won=False)
                return GuessResult(
                    outcome=GuessOutcome.WRONG,
                    match=result,
                    strikes=state.strikes,
                    max_strikes=state.max_strikes,
                    round_finished=True,
                    won=False,
                )
            return GuessResult(
                outcome=GuessOutcome.WRONG,
                match=result,
                strikes=state.strikes,
                max_strikes=state.max_strikes,
            )

        board_answer = next(a for a in state.board if a.id == result.answer_id)
        if board_answer.revealed:
            return GuessResult(outcome=GuessOutcome.ALREADY_REVEALED, match=result)

        idx = state.board.index(board_answer)
        state.board[idx] = BoardAnswer(
            id=board_answer.id,
            text=board_answer.text,
            points=board_answer.points,
            revealed=True,
        )
        state.player_scores[user_id] = state.player_scores.get(user_id, 0) + result.points
        state.player_correct[user_id] = state.player_correct.get(user_id, 0) + 1
        await user_service.record_answer(user_id, correct=True)

        if state.is_cleared:
            await self._finish_round(state, won=True)
            return GuessResult(
                outcome=GuessOutcome.CORRECT,
                match=result,
                strikes=state.strikes,
                max_strikes=state.max_strikes,
                round_finished=True,
                won=True,
            )

        return GuessResult(
            outcome=GuessOutcome.CORRECT,
            match=result,
            strikes=state.strikes,
            max_strikes=state.max_strikes,
        )

    async def use_hint(self, chat_id: int) -> BoardAnswer | None:
        """Reveal the lowest-value remaining answer at a point-value penalty."""
        state = self._rounds.get(chat_id)
        if state is None or state.finished or not state.remaining:
            return None

        weakest = min(state.remaining, key=lambda a: a.points)
        idx = state.board.index(weakest)
        penalized_points = max(
            0, int(weakest.points * (1 - config.hint_penalty_percent / 100))
        )
        state.board[idx] = BoardAnswer(
            id=weakest.id, text=weakest.text, points=penalized_points, revealed=True
        )
        state.hints_used += 1
        return state.board[idx]

    async def skip_round(self, chat_id: int) -> None:
        state = self._rounds.get(chat_id)
        if state is None:
            return
        await self._finish_round(state, won=False, aborted=True)

    async def _finish_round(
        self, state: RoundState, won: bool, aborted: bool = False
    ) -> None:
        from models.app import SessionStatus

        state.finished = True
        total_score = sum(state.player_scores.values())

        async with AppSession() as session:
            db_session = await session.get(GameSession, state.session_id)
            if db_session:
                db_session.status = (
                    SessionStatus.ABORTED if aborted else SessionStatus.FINISHED
                )
                db_session.strikes = state.strikes
                db_session.team_score = total_score
                for uid, score in state.player_scores.items():
                    session.add(
                        SessionPlayer(
                            session_id=state.session_id,
                            user_id=uid,
                            score=score,
                            correct_answers=state.player_correct.get(uid, 0),
                        )
                    )
                await session.commit()

        if aborted:
            return

        perfect = won and state.strikes == 0
        for uid in state.player_scores:
            xp_gain = config.xp_correct_answer * state.player_correct.get(uid, 0)
            if won:
                xp_gain += config.xp_win
            await user_service.award_xp(uid, xp_gain)
            await user_service.record_game_result(uid, won=won, final_score=state.player_scores[uid])
            user = await user_service.get(uid)
            if user:
                await achievement_service.evaluate_post_game(user, perfect_round=perfect)

        # If nobody scored (e.g. lost with zero correct answers), still
        # record the host's participation so losses are tracked.
        if not state.player_scores:
            await user_service.record_game_result(state.host_id, won=False, final_score=0)


game_engine = GameEngine()
