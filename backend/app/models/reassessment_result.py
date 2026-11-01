from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReassessmentResult(Base):
    __tablename__ = "reassessment_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("questions.id"), nullable=False
    )
    intervention_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("intervention_assignments.id")
    )
    reassessment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("reassessments.id", ondelete="CASCADE")
    )
    answer: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    student: Mapped[Student] = relationship(back_populates="reassessment_results")
    question: Mapped[Question] = relationship(back_populates="reassessment_results")
    intervention_assignment: Mapped[InterventionAssignment | None] = relationship(
        back_populates="reassessment_results"
    )
    reassessment: Mapped[Reassessment | None] = relationship(
        back_populates="results"
    )
