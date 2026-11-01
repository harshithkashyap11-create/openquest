"""Add intervention content, assignments, and reassessments for Milestone 4."""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_milestone_4_interventions"
down_revision: str | None = "0002_milestone_3_diagnosis"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    uuid_server_default = (
        sa.text("gen_random_uuid()")
        if op.get_bind().dialect.name == "postgresql"
        else None
    )
    with op.batch_alter_table("interventions") as batch_op:
        batch_op.add_column(
            sa.Column("group_id", sa.Uuid(as_uuid=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_interventions_group_id_learning_groups",
            "learning_groups",
            ["group_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint("uq_interventions_group_id", ["group_id"])
    op.add_column(
        "interventions",
        sa.Column("learning_objective", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "interventions",
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "interventions",
        sa.Column("introduction", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "interventions",
        sa.Column(
            "guided_example",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column(
        "interventions",
        sa.Column(
            "practice_questions",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column(
        "interventions",
        sa.Column(
            "expected_answers",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column(
        "interventions",
        sa.Column(
            "hints",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column(
        "interventions",
        sa.Column("provider", sa.Text(), server_default="template", nullable=False),
    )
    op.add_column(
        "interventions", sa.Column("generation_note", sa.Text(), nullable=True)
    )
    op.add_column(
        "intervention_assignments",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_intervention_assignments_active",
        "intervention_assignments",
        ["student_id", "intervention_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('assigned', 'in_progress')"),
        sqlite_where=sa.text("status IN ('assigned', 'in_progress')"),
    )
    op.create_table(
        "practice_responses",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_server_default,
            nullable=False,
        ),
        sa.Column("assignment_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["intervention_assignments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "question_index",
            name="uq_practice_responses_assignment_question",
        ),
    )
    op.create_table(
        "reassessments",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_server_default,
            nullable=False,
        ),
        sa.Column("assignment_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("misconception_code", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=True),
        sa.Column("incorrect_answers", sa.Integer(), nullable=True),
        sa.Column("accuracy_percentage", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'completed')", name="ck_reassessments_status"
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["intervention_assignments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", name="uq_reassessments_assignment"),
    )
    op.create_table(
        "reassessment_questions",
        sa.Column("reassessment_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reassessment_id"], ["reassessments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("reassessment_id", "question_id"),
        sa.UniqueConstraint(
            "reassessment_id", "ordinal", name="uq_reassessment_questions_ordinal"
        ),
    )
    with op.batch_alter_table("reassessment_results") as batch_op:
        batch_op.add_column(
            sa.Column("reassessment_id", sa.Uuid(as_uuid=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_reassessment_results_reassessment_id",
            "reassessments",
            ["reassessment_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("reassessment_results") as batch_op:
        batch_op.drop_constraint(
            "fk_reassessment_results_reassessment_id", type_="foreignkey"
        )
        batch_op.drop_column("reassessment_id")
    op.drop_table("reassessment_questions")
    op.drop_table("reassessments")
    op.drop_table("practice_responses")
    op.drop_index(
        "uq_intervention_assignments_active", table_name="intervention_assignments"
    )
    op.drop_column("intervention_assignments", "started_at")
    op.drop_column("interventions", "generation_note")
    op.drop_column("interventions", "provider")
    op.drop_column("interventions", "hints")
    op.drop_column("interventions", "expected_answers")
    op.drop_column("interventions", "practice_questions")
    op.drop_column("interventions", "guided_example")
    op.drop_column("interventions", "introduction")
    op.drop_column("interventions", "explanation")
    op.drop_column("interventions", "learning_objective")
    with op.batch_alter_table("interventions") as batch_op:
        batch_op.drop_constraint("uq_interventions_group_id", type_="unique")
        batch_op.drop_constraint(
            "fk_interventions_group_id_learning_groups", type_="foreignkey"
        )
        batch_op.drop_column("group_id")
