from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Class(Base):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("teacher_id", "class_name", name="uq_classes_teacher_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False
    )
    class_name: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="Mathematics"
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False, server_default="Fractions")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    teacher: Mapped[Teacher] = relationship(back_populates="classes")
    students: Mapped[list[Student]] = relationship(
        back_populates="classroom", cascade="all, delete-orphan"
    )
    learning_groups: Mapped[list[LearningGroup]] = relationship(
        back_populates="classroom", cascade="all, delete-orphan"
    )
