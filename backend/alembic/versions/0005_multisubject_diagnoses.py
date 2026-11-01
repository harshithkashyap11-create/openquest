"""Add class topics, question subjects, and structured diagnosis context."""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_multisubject_diagnoses"
down_revision: str | None = "0004_submission_attempts"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column("topic", sa.Text(), nullable=False, server_default="Fractions"),
    )
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "subject", sa.Text(), nullable=False, server_default="Mathematics"
            )
        )
        batch_op.drop_constraint("uq_questions_topic_text", type_="unique")
        batch_op.create_unique_constraint(
            "uq_questions_subject_topic_text",
            ["subject", "topic", "question_text"],
        )
    op.add_column(
        "diagnoses", sa.Column("misconception_description", sa.Text(), nullable=True)
    )
    op.add_column(
        "diagnoses",
        sa.Column("misunderstanding_explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "diagnoses", sa.Column("suggested_intervention", sa.Text(), nullable=True)
    )
    op.add_column(
        "interventions",
        sa.Column("subject", sa.Text(), nullable=False, server_default="Mathematics"),
    )


def downgrade() -> None:
    op.drop_column("interventions", "subject")
    op.drop_column("diagnoses", "suggested_intervention")
    op.drop_column("diagnoses", "misunderstanding_explanation")
    op.drop_column("diagnoses", "misconception_description")
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_constraint("uq_questions_subject_topic_text", type_="unique")
        batch_op.drop_column("subject")
        batch_op.create_unique_constraint(
            "uq_questions_topic_text", ["topic", "question_text"]
        )
    op.drop_column("classes", "topic")
