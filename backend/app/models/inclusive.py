"""Class-scoped inclusive lesson source records."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class InclusiveSource(Base):
    __tablename__ = 'inclusive_sources'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id', ondelete='CASCADE'), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id'), nullable=False)
    source: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


from sqlalchemy import Integer, Text, UniqueConstraint


class InclusiveAdaptation(Base):
    __tablename__ = 'inclusive_adaptations'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id', ondelete='CASCADE'), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('inclusive_sources.id'), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id'), nullable=False)
    supports: Mapped[list] = mapped_column(JSON, nullable=False)
    analysis: Mapped[dict] = mapped_column(JSON, nullable=False)
    draft: Mapped[dict] = mapped_column(JSON, nullable=False)
    findings: Mapped[list] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_version: Mapped[int | None] = mapped_column(Integer)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __mapper_args__ = {'version_id_col': version, 'version_id_generator': False}


class InclusiveAssignment(Base):
    __tablename__ = 'inclusive_assignments'
    __table_args__ = (UniqueConstraint('adaptation_id', 'student_id', 'version', name='uq_inclusive_assignment'),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    adaptation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('inclusive_adaptations.id'), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class InclusiveHistory(Base):
    __tablename__ = 'inclusive_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adaptation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('inclusive_adaptations.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id'), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
