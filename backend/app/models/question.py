from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint(
            "subject", "topic", "question_text", name="uq_questions_subject_topic_text"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    subject: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="Mathematics"
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_expected: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    submissions: Mapped[list[Submission]] = relationship(back_populates="question")
    reassessment_results: Mapped[list[ReassessmentResult]] = relationship(
        back_populates="question"
    )