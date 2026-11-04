import uuid
from datetime import datetime
from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class Lesson(Base):
    __tablename__ = 'lessons'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id'), index=True)
    subject: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    misconception_code: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id'))
    generation_context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class LessonRevision(Base):
    __tablename__ = 'lesson_revisions'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('lessons.id'), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(Text, default='draft')
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_note: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint('lesson_id', 'revision_no', name='uq_lesson_revision'),
        CheckConstraint("status IN ('draft','approved','published','rejected','archived')", name='ck_lesson_revision_status'),
        CheckConstraint("language IN ('en','hi','te')", name='ck_lesson_language'),
    )
    __mapper_args__ = {'version_id_col': version}

class LessonReview(Base):
    __tablename__ = 'lesson_reviews'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('lesson_revisions.id'), index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id'))
    action: Mapped[str] = mapped_column(Text)
    notes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('revision_id', 'action', name='uq_lesson_review_action'),)


class AssignedLesson(Base):
    __tablename__ = 'assigned_lessons'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('intervention_assignments.id'), index=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('lesson_revisions.id'))
    teacher_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('assignment_id', 'revision_id', name='uq_assigned_lesson_revision'),)
