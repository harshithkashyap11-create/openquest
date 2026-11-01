from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Intervention(Base):
    __tablename__ = "interventions"
    __table_args__ = (
        UniqueConstraint("group_id", name="uq_interventions_group_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "learning_groups.id",
            ondelete="CASCADE",
            name="fk_interventions_group_id_learning_groups",
        ),
    )
    subject: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="Mathematics"
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    misconception_code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    learning_objective: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    introduction: Mapped[str] = mapped_column(Text, nullable=False)
    guided_example: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    practice_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    expected_answers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    hints: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="template")
    generation_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    assignments: Mapped[list[InterventionAssignment]] = relationship(
        back_populates="intervention"
    )
