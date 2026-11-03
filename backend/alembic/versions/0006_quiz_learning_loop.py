"""Add teacher quizzes, immutable submissions, and evidence-backed reflection."""

from alembic import op
import sqlalchemy as sa

revision = "0006_quiz_learning_loop"
down_revision = "0005_multisubject_diagnoses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("lesson", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_quiz_status"),
    )
    op.create_index("ix_quizzes_class_id", "quizzes", ["class_id"])
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "quiz_id",
            sa.Uuid(),
            sa.ForeignKey("quizzes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("quiz_id", "student_id", name="uq_quiz_student_attempt"),
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])
    op.create_index("ix_quiz_attempts_student_id", "quiz_attempts", ["student_id"])
    op.create_table(
        "quiz_reflections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_id", sa.Text(), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("flagged", sa.Boolean(), nullable=False),
        sa.Column("repair_answer", sa.Integer(), nullable=True),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_quiz_reflection"),
    )
    op.create_index(
        "ix_quiz_reflections_attempt_id", "quiz_reflections", ["attempt_id"]
    )


def downgrade():
    op.drop_table("quiz_reflections")
    op.drop_table("quiz_attempts")
    op.drop_table("quizzes")
