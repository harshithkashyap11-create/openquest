import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class AuthAccount(Base):
    __tablename__ = 'auth_accounts'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey('teachers.id'), nullable=True)
    student_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey('students.id'), nullable=True)
    __table_args__ = (CheckConstraint('(teacher_id IS NULL) != (student_id IS NULL)', name='ck_account_one_role'),)

class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('auth_accounts.id'), index=True)
    csrf_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
