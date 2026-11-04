from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    InterventionAssignment,
    PracticeResponse,
)
from app.schemas.interventions import PracticeAnswer
from app.services.answer_evaluation import answers_match
from app.services.learning_service import record_evidence
from app.services.mutation_service import fingerprint


def get_owned_assignment(
    db: Session, assignment_id: UUID, student_id: UUID
) -> InterventionAssignment:
    assignment = db.scalar(
        select(InterventionAssignment)
        .where(InterventionAssignment.id == assignment_id)
        .options(
            joinedload(InterventionAssignment.intervention),
            selectinload(InterventionAssignment.practice_responses),
        )
    )
    if assignment is None:
        raise LookupError("Intervention assignment not found")
    if assignment.student_id != student_id:
        raise PermissionError("This intervention assignment does not belong to this student")
    return assignment


def submit_practice_answers(
    db: Session,
    assignment_id: UUID,
    student_id: UUID,
    answers: list[PracticeAnswer],
    *,
    commit: bool = True,
) -> tuple[InterventionAssignment, list[tuple[int, bool]]]:
    assignment = get_owned_assignment(db, assignment_id, student_id)
    if assignment.status == "completed":
        raise PermissionError("This intervention has already been completed")
    indexes = [item.question_index for item in answers]
    if len(indexes) != len(set(indexes)):
        raise ValueError("A practice question may only be answered once per submission")
    if any(index >= len(assignment.intervention.practice_questions) for index in indexes):
        raise ValueError("Practice question index is out of range")

    now = datetime.now(timezone.utc)
    if assignment.status == "assigned":
        assignment.status = "in_progress"
        assignment.started_at = now

    results: list[tuple[int, bool]] = []
    for submitted in answers:
        expected = assignment.intervention.expected_answers[submitted.question_index]
        question_text = (
            assignment.intervention.practice_questions[submitted.question_index]
            if submitted.question_index < len(assignment.intervention.practice_questions)
            else None
        )
        is_correct = answers_match(
            submitted.answer, expected, question_text=question_text
        )
        existing = db.scalar(
            select(PracticeResponse).where(
                PracticeResponse.assignment_id == assignment.id,
                PracticeResponse.question_index == submitted.question_index,
            )
        )
        if existing is None:
            existing = PracticeResponse(
                assignment_id=assignment.id,
                question_index=submitted.question_index,
            )
            db.add(existing)
        existing.answer = submitted.answer
        existing.is_correct = is_correct
        existing.submitted_at = now
        results.append((submitted.question_index, is_correct))
        record_evidence(db, assignment.student, assignment.intervention.subject, assignment.intervention.topic,
            "practice", f"practice:{assignment.id}:{submitted.question_index}:{fingerprint(submitted.answer)}", {
                "assignment_id": str(assignment.id), "question_index": submitted.question_index,
                "correct": is_correct, "assisted": True})

    if commit:
        db.commit()
        db.refresh(assignment)
    else:
        db.flush()
    return assignment, results
