"""Allow student reassessment attempts without replacing synthetic baselines."""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_submission_attempts"
down_revision: str | None = "0003_milestone_4_interventions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(
            sa.Column("attempt_no", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.drop_constraint(
            "uq_submissions_student_question", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_submissions_student_question_attempt",
            ["student_id", "question_id", "attempt_no"],
        )
        batch_op.create_check_constraint(
            "ck_submissions_attempt_no_positive", "attempt_no > 0"
        )


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_constraint(
            "ck_submissions_attempt_no_positive", type_="check"
        )
        batch_op.drop_constraint(
            "uq_submissions_student_question_attempt", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_submissions_student_question", ["student_id", "question_id"]
        )
        batch_op.drop_column("attempt_no")
