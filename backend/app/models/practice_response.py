from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PracticeResponse(Base):
    __tablename__ = "practice_responses"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id", "question_index", name="uq_practice_responses_assignment_question"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("intervention_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    intervention_assignment: Mapped[InterventionAssignment] = relationship(
        back_populates="practice_responses"
    )
