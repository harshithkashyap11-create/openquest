from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_diagnoses_confidence_range",
        ),
        CheckConstraint(
            "status IN ('provisional', 'needs_followup', 'teacher_reviewed', "
            "'confirmed', 'rejected')",
            name="ck_diagnoses_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    misconception_code: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    misconception_description: Mapped[str | None] = mapped_column(Text)
    misunderstanding_explanation: Mapped[str | None] = mapped_column(Text)
    suggested_intervention: Mapped[str | None] = mapped_column(Text)
    followup_question: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="mock")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="provisional"
    )
    model_version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    submission: Mapped[Submission] = relationship(back_populates="diagnoses")