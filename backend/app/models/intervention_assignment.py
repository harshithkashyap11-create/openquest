from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InterventionAssignment(Base):
    __tablename__ = "intervention_assignments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed')",
            name="ck_intervention_assignments_status",
        ),
        Index(
            "uq_intervention_assignments_active",
            "student_id",
            "intervention_id",
            unique=True,
            postgresql_where=text("status IN ('assigned', 'in_progress')"),
            sqlite_where=text("status IN ('assigned', 'in_progress')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    intervention_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interventions.id"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="assigned"
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    intervention: Mapped[Intervention] = relationship(back_populates="assignments")
    student: Mapped[Student] = relationship(back_populates="intervention_assignments")
    reassessment_results: Mapped[list[ReassessmentResult]] = relationship(
        back_populates="intervention_assignment"
    )
    reassessment: Mapped[Reassessment | None] = relationship(
        back_populates="intervention_assignment", uselist=False
    )
    practice_responses: Mapped[list[PracticeResponse]] = relationship(
        back_populates="intervention_assignment", cascade="all, delete-orphan"
    )
