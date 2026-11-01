from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import Diagnosis, Question, Student, Submission
from app.services.dataset_import import import_synthetic_dataset

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPOSITORY_ROOT / "data" / "synthetic_responses.csv"


def test_synthetic_dataset_import_and_idempotency(db_session):
    first = import_synthetic_dataset(db_session, DATASET_PATH)
    second = import_synthetic_dataset(db_session, DATASET_PATH)

    assert first.students_created == 40
    assert first.questions_created == 5
    assert first.submissions_created == 40
    assert second.students_created == 0
    assert second.questions_created == 0
    assert second.submissions_created == 0
    assert second.submissions_reused == 40
    assert db_session.scalar(select(func.count()).select_from(Student)) == 40
    assert db_session.scalar(select(func.count()).select_from(Question)) == 5
    assert db_session.scalar(select(func.count()).select_from(Submission)) == 40
    assert db_session.scalar(select(func.count()).select_from(Diagnosis)) == 0


def test_import_rejects_duplicate_student_question_pair(db_session, tmp_path):
    duplicate_csv = tmp_path / "duplicate.csv"
    duplicate_csv.write_text(
        "student_id,question_id,question_text,answer,explanation\n"
        "S001,Q01,Calculate 1/2 + 1/3.,5/6,worked it out\n"
        "S001,Q01,Calculate 1/2 + 1/3.,2/5,added across\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate student/question"):
        import_synthetic_dataset(db_session, duplicate_csv)