"""Add follow-up and teacher review fields for Milestone 3."""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_milestone_3_diagnosis"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diagnoses",
        sa.Column("followup_question", sa.Text(), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "provider",
            sa.Text(),
            server_default="mock",
            nullable=False,
        ),
    )
    op.add_column(
        "learning_groups",
        sa.Column(
            "review_status",
            sa.Text(),
            server_default="proposed",
            nullable=False,
        ),
    )
    with op.batch_alter_table("learning_groups") as batch_op:
        batch_op.create_check_constraint(
            "ck_learning_groups_review_status",
            "review_status IN ('proposed', 'approved', 'rejected')",
        )
    op.execute(
        "UPDATE learning_groups SET review_status = "
        "CASE WHEN teacher_approved THEN 'approved' ELSE 'proposed' END"
    )


def downgrade() -> None:
    with op.batch_alter_table("learning_groups") as batch_op:
        batch_op.drop_constraint(
            "ck_learning_groups_review_status", type_="check"
        )
    op.drop_column("learning_groups", "review_status")
    op.drop_column("diagnoses", "provider")
    op.drop_column("diagnoses", "followup_question")
