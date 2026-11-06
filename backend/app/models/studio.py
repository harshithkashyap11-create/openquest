"""Original classroom activities and their append-only student attempts."""
import uuid
from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class StudioBankItem(Base):
    __tablename__ = 'studio_bank_items'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('teachers.id', ondelete='CASCADE'), index=True)
    subject: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    question: Mapped[dict] = mapped_column(JSON)


class StudioActivity(Base):
    __tablename__ = 'studio_activities'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default='draft')
    questions: Mapped[list] = mapped_column(JSON)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudioWork(Base):
    __tablename__ = 'studio_work'
    __table_args__ = (UniqueConstraint('student_id', 'request_id', name='uq_studio_work_request'),
                      UniqueConstraint('student_id', 'activity_id', 'attempt', name='uq_studio_work_attempt'))
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id', ondelete='CASCADE'), index=True)
    activity_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('studio_activities.id', ondelete='CASCADE'), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.id', ondelete='CASCADE'), index=True)
    request_id: Mapped[str] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict] = mapped_column(JSON)
    reasoning: Mapped[dict] = mapped_column(JSON)
    media: Mapped[dict] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)
    conversations: Mapped[dict] = mapped_column(JSON, default=dict)
    lms_receipt: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudioSet(Base):
    __tablename__ = 'studio_sets'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(Text)
    activity_ids: Mapped[list] = mapped_column(JSON)
    minimum_percent: Mapped[int] = mapped_column(Integer, default=0)


class QRSession(Base):
    __tablename__ = 'studio_qr_sessions'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('classes.id', ondelete='CASCADE'), index=True)
    activity_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('studio_activities.id', ondelete='CASCADE'))
    question_id: Mapped[str] = mapped_column(Text)
    responses: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(Text, default='open')
