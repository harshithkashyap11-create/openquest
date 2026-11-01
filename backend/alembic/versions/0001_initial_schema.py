"""Create the ClassPulse Phase 1 relational schema.

Revision ID: 0001_initial
Revises:
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

uuid_type = sa.Uuid(as_uuid=True)
timestamp_default = sa.func.now()


def upgrade() -> None:
    # SQLite cannot evaluate PostgreSQL's gen_random_uuid() as a column default.
    # ORM-created UUIDs use the matching uuid.uuid4 client-side defaults.
    uuid_default = (
        sa.text("gen_random_uuid()")
        if op.get_bind().dialect.name == "postgresql"
        else None
    )
    op.create_table(
        "teachers",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_teachers_email"),
    )
    op.create_table(
        "classes",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("teacher_id", uuid_type, nullable=False),
        sa.Column("class_name", sa.Text(), nullable=False),
        sa.Column(
            "subject", sa.Text(), server_default="Mathematics", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["teachers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "teacher_id", "class_name", name="uq_classes_teacher_name"
        ),
    )
    op.create_table(
        "questions",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation_expected", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic", "question_text", name="uq_questions_topic_text"),
    )
    op.create_table(
        "interventions",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("misconception_code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "students",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("class_id", uuid_type, nullable=False),
        sa.Column("student_code", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "student_code", name="uq_students_class_code"),
    )
    op.create_table(
        "learning_groups",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("class_id", uuid_type, nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("misconception_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("teacher_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("student_id", uuid_type, nullable=False),
        sa.Column("question_id", uuid_type, nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "question_id", name="uq_submissions_student_question"
        ),
    )
    op.create_table(
        "group_members",
        sa.Column("group_id", uuid_type, nullable=False),
        sa.Column("student_id", uuid_type, nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["learning_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "student_id"),
    )
    op.create_table(
        "diagnoses",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("submission_id", uuid_type, nullable=False),
        sa.Column("misconception_code", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="provisional", nullable=False),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_diagnoses_confidence_range",
        ),
        sa.CheckConstraint(
            "status IN ('provisional', 'needs_followup', 'teacher_reviewed', "
            "'confirmed', 'rejected')",
            name="ck_diagnoses_status",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "intervention_assignments",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("intervention_id", uuid_type, nullable=False),
        sa.Column("student_id", uuid_type, nullable=False),
        sa.Column("status", sa.Text(), server_default="assigned", nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed')",
            name="ck_intervention_assignments_status",
        ),
        sa.ForeignKeyConstraint(["intervention_id"], ["interventions.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reassessment_results",
        sa.Column("id", uuid_type, server_default=uuid_default, nullable=False),
        sa.Column("student_id", uuid_type, nullable=False),
        sa.Column("question_id", uuid_type, nullable=False),
        sa.Column("intervention_assignment_id", uuid_type, nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "assessed_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["intervention_assignment_id"], ["intervention_assignments.id"]
        ),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reassessment_results")
    op.drop_table("intervention_assignments")
    op.drop_table("diagnoses")
    op.drop_table("group_members")
    op.drop_table("submissions")
    op.drop_table("learning_groups")
    op.drop_table("students")
    op.drop_table("interventions")
    op.drop_table("questions")
    op.drop_table("classes")
    op.drop_table("teachers")
