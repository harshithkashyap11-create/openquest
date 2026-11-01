import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import REPOSITORY_ROOT, get_settings
from app.models import Diagnosis, Question, Student, Submission
from app.question_catalog import QUESTION_CATALOG

GROUND_TRUTH_PATH = REPOSITORY_ROOT / "data" / "ground_truth.json"


def _normalize_label(label: str) -> str:
    return "CORRECT" if label.casefold() == "correct" else label


def evaluate_labels(
    ground_truth: list[dict[str, str]], predictions: dict[tuple[str, str], str]
) -> dict[str, Any]:
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    correct = 0
    evaluated = 0
    total_ground_truth = len(ground_truth)
    for row in ground_truth:
        key = (row["student_id"], row["question_id"])
        predicted = predictions.get(key)
        if predicted is None:
            continue
        expected = _normalize_label(row["expected_label"])
        actual = _normalize_label(predicted)
        confusion[expected][actual] += 1
        evaluated += 1
        correct += expected == actual
    return {
        "total_ground_truth": total_ground_truth,
        "total_evaluated": evaluated,
        "coverage": evaluated / total_ground_truth if total_ground_truth else 0.0,
        "correct_predictions": correct,
        "incorrect_predictions": evaluated - correct,
        "accuracy": correct / evaluated if evaluated else 0.0,
        "confusion_matrix": {
            expected: dict(sorted(counts.items()))
            for expected, counts in sorted(confusion.items())
        },
    }


def load_predictions(db: Session) -> dict[tuple[str, str], str]:
    question_id_by_text = {
        item.question_text: question_id
        for question_id, item in QUESTION_CATALOG.items()
    }
    rows = db.execute(
        select(
            Student.student_code,
            Question.question_text,
            Diagnosis.misconception_code,
        )
        .join(Submission, Submission.student_id == Student.id)
        .join(Question, Submission.question_id == Question.id)
        .join(Diagnosis, Diagnosis.submission_id == Submission.id)
        .order_by(Diagnosis.created_at.desc())
    )
    predictions: dict[tuple[str, str], str] = {}
    for student_code, question_text, code in rows:
        question_id = question_id_by_text.get(question_text)
        if question_id:
            predictions.setdefault((student_code, question_id), code)
    return predictions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare stored diagnoses with offline synthetic ground truth."
    )
    parser.add_argument(
        "--database-url",
        help="Optional database URL for evaluation; otherwise uses DATABASE_URL.",
    )
    args = parser.parse_args()
    truth = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    engine = create_engine(args.database_url or get_settings().database_url)
    try:
        with Session(engine) as db:
            report = evaluate_labels(truth, load_predictions(db))
    finally:
        engine.dispose()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
