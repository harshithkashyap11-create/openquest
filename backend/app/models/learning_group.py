from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LearningGroup(Base):
    __tablename__ = "learning_groups"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('proposed', 'approved', 'rejected')",
            name="ck_learning_groups_review_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    misconception_code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    teacher_approved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    review_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="proposed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    classroom: Mapped[Class] = relationship(back_populates="learning_groups")
    group_members: Mapped[list[GroupMember]] = relationship(
        back_populates="learning_group", cascade="all, delete-orphan"
    )
