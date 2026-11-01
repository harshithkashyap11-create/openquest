from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("class_id", "student_code", name="uq_students_class_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    student_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    classroom: Mapped[Class] = relationship(back_populates="students")
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    group_memberships: Mapped[list[GroupMember]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    intervention_assignments: Mapped[list[InterventionAssignment]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    reassessment_results: Mapped[list[ReassessmentResult]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )