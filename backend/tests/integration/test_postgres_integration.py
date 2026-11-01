import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.models import Diagnosis, Question, Student, Submission
from app.services.dataset_import import import_synthetic_dataset

pytestmark = pytest.mark.integration
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_TABLES = {
    "teachers",
    "classes",
    "students",
    "questions",
    "submissions",
    "diagnoses",
    "learning_groups",
    "group_members",
    "interventions",
    "intervention_assignments",
    "reassessment_results",
    "practice_responses",
    "reassessments",
    "reassessment_questions",
    "alembic_version",
}


def test_postgresql_migrations_and_dataset_import_are_ready():
    database_url = os.getenv("CLASS_PULSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set CLASS_PULSE_TEST_DATABASE_URL to an isolated migrated PostgreSQL test database"
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    assert engine.dialect.name == "postgresql"
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert revision in {
                "0003_milestone_4_interventions",
                "0004_submission_attempts",
            }

        inspector = inspect(engine)
        assert EXPECTED_TABLES <= set(inspector.get_table_names())
        assert {"followup_question", "provider"} <= {
            column["name"] for column in inspector.get_columns("diagnoses")
        }
        assert "review_status" in {
            column["name"] for column in inspector.get_columns("learning_groups")
        }
        assert {
            "group_id",
            "learning_objective",
            "explanation",
            "guided_example",
            "practice_questions",
            "expected_answers",
            "hints",
            "provider",
        } <= {column["name"] for column in inspector.get_columns("interventions")}
        assert "started_at" in {
            column["name"] for column in inspector.get_columns("intervention_assignments")
        }
        assert "reassessment_id" in {
            column["name"] for column in inspector.get_columns("reassessment_results")
        }
        submission_uniques = inspect(engine).get_unique_constraints("submissions")
        assert any(
            set(constraint["column_names"])
            in ({"student_id", "question_id"}, {"student_id", "question_id", "attempt_no"})
            for constraint in submission_uniques
        )

        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        dataset_path = REPOSITORY_ROOT / "data" / "synthetic_responses.csv"
        with session_factory() as session:
            first = import_synthetic_dataset(session, dataset_path)
        with session_factory() as session:
            second = import_synthetic_dataset(session, dataset_path)
            assert session.scalar(select(func.count()).select_from(Student)) == 40
            assert session.scalar(select(func.count()).select_from(Question)) == 5
            assert session.scalar(select(func.count()).select_from(Submission)) == 40
            assert session.scalar(select(func.count()).select_from(Diagnosis)) == 0

        assert first.submissions_created + first.submissions_reused == 40
        assert second.submissions_created == 0
        assert second.submissions_reused == 40
    finally:
        engine.dispose()
