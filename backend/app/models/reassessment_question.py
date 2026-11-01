from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReassessmentQuestion(Base):
    __tablename__ = "reassessment_questions"
    __table_args__ = (
        UniqueConstraint(
            "reassessment_id", "ordinal", name="uq_reassessment_questions_ordinal"
        ),
    )

    reassessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("reassessments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    reassessment: Mapped[Reassessment] = relationship(back_populates="questions")
    question: Mapped[Question] = relationship()
