"""Service layer for reading trivia questions and answers."""
from __future__ import annotations

import random

from sqlalchemy import func, select

from database import QuestionsSession
from models.questions import Answer, Question


class QuestionService:
    """Read-only access to the supplied trivia database."""

    async def get_random_question(self, category: str | None = None) -> Question | None:
        """Return a random question, optionally restricted to a category."""
        async with QuestionsSession() as session:
            stmt = select(Question)
            if category:
                stmt = stmt.where(Question.category == category)
            result = await session.execute(stmt)
            questions = result.scalars().all()
            if not questions:
                return None
            return random.choice(questions)

    async def get_question(self, question_id: int) -> Question | None:
        async with QuestionsSession() as session:
            return await session.get(Question, question_id)

    async def get_answers(self, question_id: int) -> list[Answer]:
        async with QuestionsSession() as session:
            stmt = (
                select(Answer)
                .where(Answer.question_id == question_id)
                .order_by(Answer.points.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_categories(self) -> list[str]:
        async with QuestionsSession() as session:
            result = await session.execute(select(Question.category).distinct())
            return sorted(row[0] for row in result.all())

    async def count_questions(self) -> int:
        async with QuestionsSession() as session:
            result = await session.execute(select(func.count(Question.id)))
            return int(result.scalar_one())


question_service = QuestionService()
