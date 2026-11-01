import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CheckConstraint, UniqueConstraint

from app.models import (
    Base,
    Class,
    Diagnosis,
    LearningGroup,
    Question,
    Student,
    Submission,
    Teacher,
)


def test_model_relationships(db_session):
    teacher = Teacher(name="Teacher", email="teacher@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    student = Student(student_code="S001", classroom=classroom)
    question = Question(
        topic="Fractions",
        question_text="Calculate 1/2 + 1/3.",
        correct_answer="5/6",
    )
    submission = Submission(
        student=student,
        question=question,
        answer="2/5",
        explanation="Added across.",
    )
    diagnosis = Diagnosis(
        submission=submission,
        misconception_code="M01",
        confidence=0.9,
        evidence="The explanation adds numerator and denominator.",
    )
    learning_group = LearningGroup(
        classroom=classroom,
        topic="Fractions",
        misconception_code="M01",
        name="Common denominator practice",
    )

    db_session.add_all([teacher, question, learning_group, diagnosis])
    db_session.flush()

    assert classroom.teacher is teacher
    assert student in classroom.students
    assert submission in student.submissions
    assert diagnosis in submission.diagnoses
    assert learning_group.classroom is classroom
    assert isinstance(teacher.id, uuid.UUID)


def test_required_unique_and_check_constraints_exist():
    submission_constraints = Base.metadata.tables["submissions"].constraints
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        in ({"student_id", "question_id"}, {"student_id", "question_id", "attempt_no"})
        for constraint in submission_constraints
    )

    diagnosis_constraints = Base.metadata.tables["diagnoses"].constraints
    assert sum(
        isinstance(constraint, CheckConstraint)
        for constraint in diagnosis_constraints
    ) >= 2
    assert Base.metadata.tables["students"].c.created_at.type.timezone is True


def test_database_rejects_duplicate_student_question_submission(db_session):
    teacher = Teacher(name="Teacher", email="unique@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    student = Student(student_code="S001", classroom=classroom)
    question = Question(
        topic="Fractions",
        question_text="Unique check",
        correct_answer="1/2",
    )
    db_session.add_all([teacher, student, question])
    db_session.flush()
    db_session.add(
        Submission(student=student, question=question, answer="1/2")
    )
    db_session.flush()
    db_session.add(
        Submission(student=student, question=question, answer="2/4")
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
