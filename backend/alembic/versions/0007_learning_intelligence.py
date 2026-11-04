"""learning_intelligence

Revision ID: 0007_learning_intelligence
Revises: 0006_quiz_learning_loop
Create Date: 2026-11-03 18:54:01.771331
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007_learning_intelligence'
down_revision: Union[str, None] = '0006_quiz_learning_loop'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('mutation_receipts',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('fingerprint', sa.Text(), nullable=False),
    sa.Column('response', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lessons',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('class_id', sa.Uuid(), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('topic', sa.Text(), nullable=False),
    sa.Column('misconception_code', sa.Text(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('generation_context', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['teachers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lessons_class_id'), 'lessons', ['class_id'], unique=False)
    op.create_table('auth_accounts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('username', sa.Text(), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('teacher_id', sa.Uuid(), nullable=True),
    sa.Column('student_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint('(teacher_id IS NULL) != (student_id IS NULL)', name='ck_account_one_role'),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('learner_states',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('topic', sa.Text(), nullable=False),
    sa.Column('projection', sa.JSON(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('student_id', 'subject', 'topic', name='uq_learner_topic')
    )
    op.create_index(op.f('ix_learner_states_student_id'), 'learner_states', ['student_id'], unique=False)
    op.create_table('learning_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('topic', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('source_key', sa.Text(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_key')
    )
    op.create_index(op.f('ix_learning_events_student_id'), 'learning_events', ['student_id'], unique=False)
    op.create_table('learning_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('topic', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('student_id', 'subject', 'topic', name='uq_session_topic')
    )
    op.create_index(op.f('ix_learning_sessions_student_id'), 'learning_sessions', ['student_id'], unique=False)
    op.create_table('lesson_revisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('lesson_id', sa.Uuid(), nullable=False),
    sa.Column('revision_no', sa.Integer(), nullable=False),
    sa.Column('language', sa.Text(), nullable=False),
    sa.Column('content', sa.JSON(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('provider', sa.Text(), nullable=False),
    sa.Column('model', sa.Text(), nullable=True),
    sa.Column('generation_note', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("language IN ('en','hi','te')", name='ck_lesson_language'),
    sa.CheckConstraint("status IN ('draft','approved','published','rejected','archived')", name='ck_lesson_revision_status'),
    sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('lesson_id', 'revision_no', name='uq_lesson_revision')
    )
    op.create_index(op.f('ix_lesson_revisions_lesson_id'), 'lesson_revisions', ['lesson_id'], unique=False)
    op.create_table('auth_sessions',
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('account_id', sa.Uuid(), nullable=False),
    sa.Column('csrf_token', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['auth_accounts.id'], ),
    sa.PrimaryKeyConstraint('token_hash')
    )
    op.create_index(op.f('ix_auth_sessions_account_id'), 'auth_sessions', ['account_id'], unique=False)
    op.create_table('learning_decisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('requires_teacher_approval', sa.Boolean(), nullable=False),
    sa.Column('policy_version', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['learning_events.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id')
    )
    op.create_table('lesson_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('revision_id', sa.Uuid(), nullable=False),
    sa.Column('teacher_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('notes', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['revision_id'], ['lesson_revisions.id'], ),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('revision_id', 'action', name='uq_lesson_review_action')
    )
    op.create_index(op.f('ix_lesson_reviews_revision_id'), 'lesson_reviews', ['revision_id'], unique=False)
    op.create_table('diagnosis_corrections',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('diagnosis_id', sa.Uuid(), nullable=False),
    sa.Column('teacher_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('request_id', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('diagnosis_id', 'version', name='uq_diagnosis_correction_version'),
    sa.UniqueConstraint('request_id')
    )
    op.create_index(op.f('ix_diagnosis_corrections_diagnosis_id'), 'diagnosis_corrections', ['diagnosis_id'], unique=False)

    op.create_table('assigned_lessons',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('assignment_id', sa.Uuid(), sa.ForeignKey('intervention_assignments.id'), nullable=False),
        sa.Column('revision_id', sa.Uuid(), sa.ForeignKey('lesson_revisions.id'), nullable=False),
        sa.Column('teacher_id', sa.Uuid(), sa.ForeignKey('teachers.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('assignment_id', 'revision_id', name='uq_assigned_lesson_revision'))
    op.create_index('ix_assigned_lessons_assignment_id', 'assigned_lessons', ['assignment_id'])


def downgrade() -> None:
    op.drop_table('assigned_lessons')
    op.drop_index(op.f('ix_diagnosis_corrections_diagnosis_id'), table_name='diagnosis_corrections')
    op.drop_table('diagnosis_corrections')
    op.drop_index(op.f('ix_lesson_reviews_revision_id'), table_name='lesson_reviews')
    op.drop_table('lesson_reviews')
    op.drop_table('learning_decisions')
    op.drop_index(op.f('ix_auth_sessions_account_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_index(op.f('ix_lesson_revisions_lesson_id'), table_name='lesson_revisions')
    op.drop_table('lesson_revisions')
    op.drop_index(op.f('ix_learning_sessions_student_id'), table_name='learning_sessions')
    op.drop_table('learning_sessions')
    op.drop_index(op.f('ix_learning_events_student_id'), table_name='learning_events')
    op.drop_table('learning_events')
    op.drop_index(op.f('ix_learner_states_student_id'), table_name='learner_states')
    op.drop_table('learner_states')
    op.drop_table('auth_accounts')
    op.drop_index(op.f('ix_lessons_class_id'), table_name='lessons')
    op.drop_table('lessons')
    op.drop_table('mutation_receipts')
