import csv
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Class, Question, Student, Submission, Teacher
from app.question_catalog import QUESTION_CATALOG

DEMO_TEACHER_NAME = "ClassPulse Synthetic Demo Teacher"
DEMO_TEACHER_EMAIL = "demo.teacher@classpulse.local"
DEMO_CLASS_NAME = "Fractions Synthetic Demo Class"
DEMO_CLASS_SUBJECT = "Mathematics"
ID_NAMESPACE = uuid.UUID("da70e84c-19a4-4a2d-a178-4bfc0b6d5044")
REQUIRED_COLUMNS = {
    "student_id",
    "question_id",
    "question_text",
    "answer",
    "explanation",
}


@dataclass(frozen=True)
class ImportSummary:
    teachers_created: int = 0
    classes_created: int = 0
    students_created: int = 0
    questions_created: int = 0
    submissions_created: int = 0
    submissions_reused: int = 0


def _stable_id(key: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, key)


def _read_rows(csv_path: Path) -> list[dict[str, str | None]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Synthetic dataset not found: {csv_path}")

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Dataset is missing required columns: {missing}")
        return [
            row
            for row in reader
            if any((value or "").strip() for value in row.values() if value is not None)
        ]


def import_synthetic_dataset(
    db: Session, csv_path: Path, *, teacher_id: uuid.UUID | None = None
) -> ImportSummary:
    rows = _read_rows(csv_path)
    if not rows:
        raise ValueError("Synthetic dataset contains no response rows")

    pairs: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        student_code = (row.get("student_id") or "").strip()
        question_id = (row.get("question_id") or "").strip()
        question_text = (row.get("question_text") or "").strip()
        if not student_code or not question_id or not question_text:
            raise ValueError(f"Dataset row {row_number} has a missing identifier or prompt")
        if question_id not in QUESTION_CATALOG:
            raise ValueError(
                f"Dataset row {row_number} references unknown question {question_id!r}"
            )
        if question_text != QUESTION_CATALOG[question_id].question_text:
            raise ValueError(
                f"Dataset row {row_number} prompt does not match catalog entry {question_id}"
            )
        pair = (student_code, question_id)
        if pair in pairs:
            raise ValueError(
                f"Dataset contains duplicate student/question response: {pair}"
            )
        pairs.add(pair)

    counts = {
        "teachers_created": 0,
        "classes_created": 0,
        "students_created": 0,
        "questions_created": 0,
        "submissions_created": 0,
        "submissions_reused": 0,
    }

    with db.begin():
        teacher = (db.get(Teacher, teacher_id) if teacher_id is not None else
                   db.scalar(select(Teacher).where(Teacher.email == DEMO_TEACHER_EMAIL)))
        if teacher_id is not None and teacher is None:
            raise ValueError("Selected teacher does not exist")
        if teacher is None:
            teacher = Teacher(
                id=_stable_id(f"teacher:{DEMO_TEACHER_EMAIL}"),
                name=DEMO_TEACHER_NAME,
                email=DEMO_TEACHER_EMAIL,
            )
            db.add(teacher)
            db.flush()
            counts["teachers_created"] += 1
        elif teacher_id is None and teacher.name != DEMO_TEACHER_NAME:
            raise ValueError("Existing demo teacher has unexpected identifying details")

        classrooms: dict[tuple[str, str], Class] = {}
        students: dict[tuple[str, str, str], Student] = {}
        questions: dict[str, Question] = {}
        for row in rows:
            student_code = (row["student_id"] or "").strip()
            question_id = (row["question_id"] or "").strip()
            catalog_entry = QUESTION_CATALOG[question_id]

            class_key = (catalog_entry.subject, catalog_entry.topic)
            class_name = (
                DEMO_CLASS_NAME
                if class_key == (DEMO_CLASS_SUBJECT, "Fractions")
                else f"{catalog_entry.topic} Synthetic Demo Class"
            )
            classroom = classrooms.get(class_key)
            if classroom is None:
                classroom = db.scalar(
                    select(Class).where(
                        Class.teacher_id == teacher.id,
                        Class.class_name == class_name,
                    )
                )
                if classroom is None:
                    classroom = Class(
                        id=_stable_id(
                            f"class:{DEMO_TEACHER_EMAIL}:{class_name}"
                        ),
                        teacher_id=teacher.id,
                        class_name=class_name,
                        subject=catalog_entry.subject,
                        topic=catalog_entry.topic,
                    )
                    db.add(classroom)
                    db.flush()
                    counts["classes_created"] += 1
                elif (
                    classroom.subject != catalog_entry.subject
                    or classroom.topic != catalog_entry.topic
                ):
                    raise ValueError("Existing demo class has unexpected subject/topic")
                classrooms[class_key] = classroom

            student_key = (*class_key, student_code)
            student = students.get(student_key)
            if student is None:
                student = db.scalar(
                    select(Student).where(
                        Student.class_id == classroom.id,
                        Student.student_code == student_code,
                    )
                )
                if student is None:
                    student = Student(
                        id=_stable_id(
                            f"student:{class_name}:{student_code}"
                        ),
                        class_id=classroom.id,
                        student_code=student_code,
                    )
                    db.add(student)
                    db.flush()
                    counts["students_created"] += 1
                students[student_key] = student

            question = questions.get(question_id)
            if question is None:
                question = db.scalar(
                    select(Question).where(
                        Question.subject == catalog_entry.subject,
                        Question.topic == catalog_entry.topic,
                        Question.question_text == catalog_entry.question_text,
                    )
                )
                if question is None:
                    question = Question(
                        id=_stable_id(f"question:{question_id}"),
                        subject=catalog_entry.subject,
                        topic=catalog_entry.topic,
                        question_text=catalog_entry.question_text,
                        correct_answer=catalog_entry.correct_answer,
                        explanation_expected=catalog_entry.explanation_expected,
                    )
                    db.add(question)
                    db.flush()
                    counts["questions_created"] += 1
                elif (
                    question.correct_answer != catalog_entry.correct_answer
                    or question.explanation_expected
                    != catalog_entry.explanation_expected
                ):
                    raise ValueError(
                        f"Existing question {question_id} conflicts with the reviewed catalog"
                    )
                questions[question_id] = question

            answer = (row["answer"] or "").strip() or None
            explanation = (row["explanation"] or "").strip() or None
            submission = db.scalar(
                select(Submission).where(
                    Submission.student_id == student.id,
                    Submission.question_id == question.id,
                )
            )
            if submission is None:
                db.add(
                    Submission(
                        id=_stable_id(f"submission:{student_code}:{question_id}"),
                        student_id=student.id,
                        question_id=question.id,
                        answer=answer,
                        explanation=explanation,
                    )
                )
                counts["submissions_created"] += 1
            else:
                if submission.answer != answer or submission.explanation != explanation:
                    raise ValueError(
                        f"Existing submission for {student_code}/{question_id} "
                        "differs from the dataset"
                    )
                counts["submissions_reused"] += 1

    return ImportSummary(**counts)
