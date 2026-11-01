from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Reassessment(Base):
    __tablename__ = "reassessments"
    __table_args__ = (
        UniqueConstraint("assignment_id", name="uq_reassessments_assignment"),
        CheckConstraint(
            "status IN ('pending', 'completed')", name="ck_reassessments_status"
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
    misconception_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending"
    )
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int | None] = mapped_column(Integer)
    incorrect_answers: Mapped[int | None] = mapped_column(Integer)
    accuracy_percentage: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    intervention_assignment: Mapped[InterventionAssignment] = relationship(
        back_populates="reassessment"
    )
    questions: Mapped[list[ReassessmentQuestion]] = relationship(
        back_populates="reassessment",
        cascade="all, delete-orphan",
        order_by="ReassessmentQuestion.ordinal",
    )
    results: Mapped[list[ReassessmentResult]] = relationship(
        back_populates="reassessment", cascade="all, delete-orphan"
    )
