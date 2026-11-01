import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.models import Teacher


BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "teachers",
    "classes",
    "students",
    "questions",
    "submissions",
    "diagnoses",
    "learning_groups",
    "interventions",
    "intervention_assignments",
    "reassessment_results",
    "group_members",
    "practice_responses",
    "reassessments",
    "reassessment_questions",
}


def _run_alembic(database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "AI_PROVIDER": "mock",
            "OPENROUTER_API_KEY": "",
            "OPENROUTER_MODEL": "",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )


def test_all_migrations_apply_to_empty_sqlite_and_models_can_query(tmp_path):
    database_path = tmp_path / "empty.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path}"

    _run_alembic(database_url, "upgrade", "head")
    current = _run_alembic(database_url, "current")
    _run_alembic(database_url, "check")

    assert "0005_multisubject_diagnoses (head)" in current.stdout

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert EXPECTED_TABLES <= set(inspector.get_table_names())
        assert {"subject", "topic"} <= {
            column["name"] for column in inspector.get_columns("classes")
        }
        assert "subject" in {
            column["name"] for column in inspector.get_columns("questions")
        }
        assert {
            "misconception_description",
            "misunderstanding_explanation",
            "suggested_intervention",
        } <= {
            column["name"] for column in inspector.get_columns("diagnoses")
        }
        for table_name in EXPECTED_TABLES:
            id_column = next(
                (
                    column
                    for column in inspector.get_columns(table_name)
                    if column["name"] == "id"
                ),
                None,
            )
            if id_column is not None:
                assert "gen_random_uuid" not in str(id_column["default"])

        with Session(engine) as session:
            teacher = Teacher(name="SQLite migration test", email="sqlite@example.test")
            session.add(teacher)
            session.commit()

            queried_teacher = session.scalar(
                select(Teacher).where(Teacher.email == "sqlite@example.test")
            )
            assert queried_teacher is not None
            assert queried_teacher.id == teacher.id
    finally:
        engine.dispose()


def test_multisubject_migration_preserves_existing_rows_and_adds_defaults(tmp_path):
    database_path = tmp_path / "populated.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _run_alembic(database_url, "upgrade", "0004_submission_attempts")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO teachers (id, name, email) VALUES (:id, :name, :email)"),
                {"id": "teacher-1", "name": "Existing teacher", "email": "existing@test"},
            )
            connection.execute(
                text(
                    "INSERT INTO classes (id, teacher_id, class_name) "
                    "VALUES (:id, :teacher_id, :class_name)"
                ),
                {"id": "class-1", "teacher_id": "teacher-1", "class_name": "Existing class"},
            )
            connection.execute(
                text(
                    "INSERT INTO students (id, class_id, student_code) "
                    "VALUES (:id, :class_id, :student_code)"
                ),
                {"id": "student-1", "class_id": "class-1", "student_code": "OLD001"},
            )
            connection.execute(
                text(
                    "INSERT INTO questions (id, topic, question_text, correct_answer) "
                    "VALUES (:id, :topic, :question_text, :correct_answer)"
                ),
                {
                    "id": "question-1",
                    "topic": "Fractions",
                    "question_text": "Existing question",
                    "correct_answer": "1/2",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO submissions (id, student_id, question_id) "
                    "VALUES (:id, :student_id, :question_id)"
                ),
                {
                    "id": "submission-1",
                    "student_id": "student-1",
                    "question_id": "question-1",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO diagnoses "
                    "(id, submission_id, misconception_code, confidence, evidence) "
                    "VALUES (:id, :submission_id, :code, :confidence, :evidence)"
                ),
                {
                    "id": "diagnosis-1",
                    "submission_id": "submission-1",
                    "code": "M01",
                    "confidence": 0.9,
                    "evidence": "Existing evidence",
                },
            )
    finally:
        engine.dispose()

    _run_alembic(database_url, "upgrade", "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT student_code FROM students WHERE id = 'student-1'")
            ) == "OLD001"
            assert connection.scalar(
                text("SELECT topic FROM classes WHERE id = 'class-1'")
            ) == "Fractions"
            assert connection.scalar(
                text("SELECT subject FROM questions WHERE id = 'question-1'")
            ) == "Mathematics"
            assert connection.scalar(
                text(
                    "SELECT evidence FROM diagnoses WHERE id = 'diagnosis-1'"
                )
            ) == "Existing evidence"
            assert connection.scalar(
                text(
                    "SELECT misconception_description FROM diagnoses "
                    "WHERE id = 'diagnosis-1'"
                )
            ) is None
    finally:
        engine.dispose()
