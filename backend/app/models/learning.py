"""Additive, replayable educational evidence and versioned projections."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LearningEvent(Base):
    __tablename__ = "learning_events"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    source_key: Mapped[str] = mapped_column(Text, unique=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearnerState(Base):
    __tablename__ = "learner_states"
    __table_args__ = (UniqueConstraint("student_id", "subject", "topic", name="uq_learner_topic"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    projection: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (UniqueConstraint("student_id", "subject", "topic", name="uq_session_topic"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, default="CREATED")
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class LearningDecision(Base):
    __tablename__ = "learning_decisions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("learning_events.id"), unique=True)
    action: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    requires_teacher_approval: Mapped[bool] = mapped_column(Boolean)
    policy_version: Mapped[str] = mapped_column(Text, default="evidence-v1")
    source: Mapped[str] = mapped_column(Text, default="deterministic_policy")
    status: Mapped[str] = mapped_column(Text, default="recommended")


class MutationReceipt(Base):
    __tablename__ = "mutation_receipts"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(Text)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiagnosisCorrection(Base):
    __tablename__ = "diagnosis_corrections"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("diagnoses.id"), index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("teachers.id"))
    code: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("diagnosis_id", "version", name="uq_diagnosis_correction_version"),)
