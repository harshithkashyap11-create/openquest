import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Diagnosis,
    InterventionAssignment,
    Reassessment,
    Student,
    Submission,
)
from app.question_catalog import QUESTION_CATALOG
from app.services.answer_evaluation import answers_match

SUPPORT_ACCURACY_THRESHOLD = 70.0
ID_NAMESPACE = UUID("da70e84c-19a4-4a2d-a178-4bfc0b6d5044")

CATALOG_BY_ID = {
    uuid.uuid5(ID_NAMESPACE, f"question:{qid}"): catalog_question
    for qid, catalog_question in QUESTION_CATALOG.items()
}
CATALOG_BY_TEXT = {
    catalog_question.question_text: catalog_question
    for catalog_question in QUESTION_CATALOG.values()
}


def _is_initial_submission_correct(submission: Submission) -> bool:
    if submission.answer is None or not submission.answer.strip():
        return False

    catalog_entry = CATALOG_BY_ID.get(submission.question_id)
    if catalog_entry is None and submission.question:
        catalog_entry = CATALOG_BY_ID.get(
            submission.question.id
        ) or CATALOG_BY_TEXT.get(submission.question.question_text)

    acceptable_answers: list[str] = []
    if catalog_entry:
        acceptable_answers = [
            catalog_entry.correct_answer,
            *catalog_entry.accepted_answers,
        ]
    elif submission.question and submission.question.correct_answer:
        acceptable_answers = [submission.question.correct_answer]

    submitted_answer = submission.answer.strip()
    question_text = (
        submission.question.question_text if submission.question else None
    )

    for expected in acceptable_answers:
        if submitted_answer.casefold() == expected.strip().casefold():
            return True
        if answers_match(
            submitted_answer, expected, question_text=question_text
        ):
            return True

    return False


def _accuracy(correct: int, sample_size: int) -> float | None:
    if sample_size == 0:
        return None
    return round(correct * 100 / sample_size, 1)


def get_class_progress(db: Session, class_id: UUID) -> dict:
    assignments = list(
        db.scalars(
            select(InterventionAssignment)
            .join(InterventionAssignment.student)
            .where(Student.class_id == class_id)
            .options(
                joinedload(InterventionAssignment.intervention),
                joinedload(InterventionAssignment.student),
                joinedload(InterventionAssignment.reassessment),
            )
        ).unique()
    )
    initial_submissions = list(
        db.scalars(
            select(Submission)
            .join(Submission.student)
            .where(Student.class_id == class_id, Submission.attempt_no == 1)
            .options(joinedload(Submission.question))
        )
    )
    initial_correct = sum(
        _is_initial_submission_correct(submission)
        for submission in initial_submissions
    )

    completed_reassessments = [
        assignment.reassessment
        for assignment in assignments
        if assignment.reassessment is not None
        and assignment.reassessment.status == "completed"
    ]
    followup_correct = sum(
        reassessment.correct_answers or 0
        for reassessment in completed_reassessments
    )
    followup_sample_size = sum(
        reassessment.total_questions for reassessment in completed_reassessments
    )

    latest_by_student: dict[UUID, Reassessment] = {}
    for reassessment in db.scalars(
        select(Reassessment)
        .join(Reassessment.intervention_assignment)
        .join(InterventionAssignment.student)
        .where(Student.class_id == class_id)
        .options(
            joinedload(Reassessment.intervention_assignment).joinedload(
                InterventionAssignment.student
            )
        )
        .order_by(Reassessment.created_at.desc(), Reassessment.id)
    ).unique():
        latest_by_student.setdefault(
            reassessment.intervention_assignment.student_id, reassessment
        )

    support: dict[UUID, dict] = {}
    for student_id, reassessment in latest_by_student.items():
        score = reassessment.accuracy_percentage
        if reassessment.status == "pending":
            reason = "Reassessment not yet completed"
        elif score is not None and score < SUPPORT_ACCURACY_THRESHOLD:
            reason = "Follow-up accuracy is below the 70% support threshold"
        else:
            continue
        student = reassessment.intervention_assignment.student
        support[student_id] = {
            "student_id": student_id,
            "student_code": student.student_code,
            "misconception_code": reassessment.misconception_code,
            "reason": reason,
            "followup_accuracy_percentage": score,
            "sample_size": reassessment.total_questions
            if reassessment.status == "completed"
            else 0,
        }

    followup_diagnoses = db.scalars(
        select(Diagnosis)
        .join(Diagnosis.submission)
        .join(Submission.student)
        .where(
            Student.class_id == class_id,
            (Diagnosis.misconception_code == "M06")
            | (Diagnosis.status == "needs_followup"),
        )
        .options(
            joinedload(Diagnosis.submission).joinedload(Submission.student)
        )
        .order_by(Diagnosis.created_at.desc())
    ).unique()
    for diagnosis in followup_diagnoses:
        student = diagnosis.submission.student
        support.setdefault(
            student.id,
            {
                "student_id": student.id,
                "student_code": student.student_code,
                "misconception_code": diagnosis.misconception_code,
                "reason": "Diagnostic follow-up required for uncertain evidence",
                "followup_accuracy_percentage": None,
                "sample_size": 0,
            },
        )

    initial_accuracy = _accuracy(initial_correct, len(initial_submissions))
    followup_accuracy = _accuracy(followup_correct, followup_sample_size)
    change = (
        round(followup_accuracy - initial_accuracy, 1)
        if initial_accuracy is not None and followup_accuracy is not None
        else None
    )
    return {
        "class_id": class_id,
        "assigned_interventions": len(assignments),
        "completed_interventions": sum(
            assignment.status == "completed" for assignment in assignments
        ),
        "completed_reassessments": len(completed_reassessments),
        "initial_assessment": {
            "accuracy_percentage": initial_accuracy,
            "sample_size": len(initial_submissions),
            "correct_answers": initial_correct,
        },
        "followup_assessment": {
            "accuracy_percentage": followup_accuracy,
            "sample_size": followup_sample_size,
            "correct_answers": followup_correct,
        },
        "accuracy_change_percentage_points": change,
        "progress_interpretation": (
            "Observed score change only; sample sizes may be small and do not "
            "establish causal improvement."
        ),
        "students_needing_support": list(support.values()),
    }


def get_student_progress(db: Session, student_id: UUID) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise LookupError("Student not found")
    initial = list(
        db.scalars(
            select(Submission)
            .where(
                Submission.student_id == student_id,
                Submission.attempt_no == 1,
            )
            .options(joinedload(Submission.question))
        )
    )
    initial_correct = sum(
        _is_initial_submission_correct(item) for item in initial
    )
    assignments = list(
        db.scalars(
            select(InterventionAssignment)
            .where(InterventionAssignment.student_id == student_id)
            .options(joinedload(InterventionAssignment.reassessment))
        )
    )
    reassessments = [
        item.reassessment
        for item in assignments
        if item.reassessment is not None
        and item.reassessment.status == "completed"
    ]
    followup_correct = sum(item.correct_answers or 0 for item in reassessments)
    followup_sample_size = sum(item.total_questions for item in reassessments)
    initial_accuracy = _accuracy(initial_correct, len(initial))
    followup_accuracy = _accuracy(followup_correct, followup_sample_size)
    return {
        "student_id": student.id,
        "student_code": student.student_code,
        "assigned_interventions": len(assignments),
        "completed_interventions": sum(
            item.status == "completed" for item in assignments
        ),
        "completed_reassessments": len(reassessments),
        "initial_assessment": {
            "accuracy_percentage": initial_accuracy,
            "sample_size": len(initial),
            "correct_answers": initial_correct,
        },
        "followup_assessment": {
            "accuracy_percentage": followup_accuracy,
            "sample_size": followup_sample_size,
            "correct_answers": followup_correct,
        },
        "accuracy_change_percentage_points": (
            round(followup_accuracy - initial_accuracy, 1)
            if initial_accuracy is not None and followup_accuracy is not None
            else None
        ),
        "progress_interpretation": (
            "Observed score change only; sample sizes may be small and do not "
            "establish causal improvement."
        ),
    }
