"""
ORM models mirroring the supplied ``anime_family_feud_200.db`` schema.

These models are read-only from the bot's perspective: the bot never
inserts, updates, or deletes rows here through normal gameplay. Admins may
extend the underlying database out-of-band (or via the admin panel's
"Add Question" feature, which writes through the same session but is kept
as an explicit, deliberate operation).

Schema (as shipped):

    questions(id INTEGER PK, category TEXT, question TEXT)
    answers(id INTEGER PK, question_id INTEGER FK, answer TEXT, points INTEGER)
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import QuestionsBase


class Question(QuestionsBase):
    """A single Family Feud-style prompt, e.g. 'Name a famous Shonen anime'."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False)

    answers: Mapped[list["Answer"]] = relationship(
        back_populates="question",
        order_by="Answer.points.desc()",
        lazy="selectin",
    )


class Answer(QuestionsBase):
    """One ranked answer on the board for a given question."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    answer: Mapped[str] = mapped_column(String, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped["Question"] = relationship(back_populates="answers")
