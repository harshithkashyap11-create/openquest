from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.models import (
    Class,
    InterventionAssignment,
    Reassessment,
    ReassessmentQuestion,
)
from app.schemas.interventions import (
    ClassProgressResponse,
    InterventionAssignmentResponse,
    InterventionCompletionResponse,
    InterventionContentResponse,
    InterventionGenerationResponse,
    PracticeResponseItem,
    PracticeResultResponse,
    PracticeSubmissionRequest,
    PracticeSubmissionResponse,
    ReassessmentQuestionResponse,
    ReassessmentResponse,
    ReassessmentResultResponse,
    ReassessmentSubmissionRequest,
    ReassessmentSubmissionResponse,
    StudentInterventionResponse,
)
from app.services.intervention_assignment_service import (
    get_owned_assignment,
    submit_practice_answers,
)
from app.services.intervention_service import (
    InterventionNotAllowedError,
    generate_intervention_for_group,
)
from app.services.diagnosis_provider import ProviderError
from app.services.progress_service import get_class_progress
from app.services.reassessment_service import (
    generate_reassessment,
    submit_reassessment,
)

router = APIRouter(prefix="/api", tags=["interventions"])


def _intervention_content(intervention) -> InterventionContentResponse:
    return InterventionContentResponse(
        id=intervention.id,
        group_id=intervention.group_id,
        subject=intervention.subject,
        topic=intervention.topic,
        misconception_code=intervention.misconception_code,
        title=intervention.title,
        learning_objective=intervention.learning_objective,
        explanation=intervention.explanation,
        introduction=intervention.introduction,
        guided_example=intervention.guided_example,
        practice_questions=intervention.practice_questions,
        expected_answers=intervention.expected_answers,
        instructions=intervention.instructions,
        hints=intervention.hints,
        provider=intervention.provider,
        generation_note=intervention.generation_note,
    )


def _student_intervention(intervention) -> StudentInterventionResponse:
    return StudentInterventionResponse(
        id=intervention.id,
        subject=intervention.subject,
        topic=intervention.topic,
        misconception_code=intervention.misconception_code,
        title=intervention.title,
        learning_objective=intervention.learning_objective,
        explanation=intervention.explanation,
        introduction=intervention.introduction,
        guided_example=intervention.guided_example,
        practice_questions=[
            {
                "question_index": index,
                "question": question,
                "hint": intervention.hints[min(index, len(intervention.hints) - 1)],
            }
            for index, question in enumerate(intervention.practice_questions)
        ],
        instructions=intervention.instructions,
    )


def _assignment_response(assignment) -> InterventionAssignmentResponse:
    practice_responses = [
        PracticeResponseItem(
            question_index=resp.question_index,
            answer=resp.answer,
            is_correct=resp.is_correct,
            submitted_at=resp.submitted_at.isoformat(),
        )
        for resp in sorted(
            getattr(assignment, "practice_responses", []) or [],
            key=lambda r: r.question_index,
        )
    ]
    return InterventionAssignmentResponse(
        id=assignment.id,
        intervention_id=assignment.intervention_id,
        student_id=assignment.student_id,
        status=assignment.status,
        assigned_at=assignment.assigned_at.isoformat(),
        started_at=(
            assignment.started_at.isoformat() if assignment.started_at else None
        ),
        completed_at=(
            assignment.completed_at.isoformat() if assignment.completed_at else None
        ),
        intervention=_student_intervention(assignment.intervention),
        practice_responses=practice_responses,
    )


def _reassessment_response(reassessment: Reassessment) -> ReassessmentResponse:
    return ReassessmentResponse(
        id=reassessment.id,
        assignment_id=reassessment.assignment_id,
        misconception_code=reassessment.misconception_code,
        status=reassessment.status,
        questions=[
            ReassessmentQuestionResponse(
                id=item.question_id,
                question=item.question.question_text,
            )
            for item in reassessment.questions
        ],
        total_questions=reassessment.total_questions,
        correct_answers=reassessment.correct_answers,
        incorrect_answers=reassessment.incorrect_answers,
        accuracy_percentage=reassessment.accuracy_percentage,
        results=[
            ReassessmentResultResponse(
                question_id=result.question_id,
                answer=result.answer,
                is_correct=result.is_correct,
            )
            for result in (getattr(reassessment, "results", None) or [])
        ],
    )


def _student_identity(student_id: UUID, asserted_student_id: UUID) -> None:
    if student_id != asserted_student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student identity does not match the requested resource",
        )


def _owned_assignment_or_404(
    db: Session, assignment_id: UUID, student_id: UUID
) -> InterventionAssignment:
    try:
        return get_owned_assignment(db, assignment_id, student_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post(
    "/groups/{group_id}/interventions/generate",
    response_model=InterventionGenerationResponse,
)
def generate_group_intervention(
    group_id: UUID, db: Session = Depends(get_db)
) -> InterventionGenerationResponse:
    try:
        intervention, assignments, created = generate_intervention_for_group(
            db, group_id
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InterventionNotAllowedError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    return InterventionGenerationResponse(
        intervention=_intervention_content(intervention),
        assignments_created=created,
        assignments=[_assignment_response(item) for item in assignments],
    )


@router.get(
    "/students/{student_id}/interventions",
    response_model=list[InterventionAssignmentResponse],
)
def list_student_interventions(
    student_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> list[InterventionAssignmentResponse]:
    _student_identity(student_id, asserted_student_id)
    assignments = db.scalars(
        select(InterventionAssignment)
        .where(InterventionAssignment.student_id == student_id)
        .options(
            joinedload(InterventionAssignment.intervention),
            selectinload(InterventionAssignment.practice_responses),
        )
        .order_by(InterventionAssignment.assigned_at.desc())
    )
    return [_assignment_response(item) for item in assignments]


@router.get(
    "/intervention-assignments/{assignment_id}",
    response_model=InterventionAssignmentResponse,
)
def get_intervention_assignment(
    assignment_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> InterventionAssignmentResponse:
    assignment = _owned_assignment_or_404(db, assignment_id, asserted_student_id)
    return _assignment_response(assignment)


@router.post(
    "/intervention-assignments/{assignment_id}/submit",
    response_model=PracticeSubmissionResponse,
)
def submit_intervention_answers(
    assignment_id: UUID,
    payload: PracticeSubmissionRequest,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> PracticeSubmissionResponse:
    try:
        assignment, results = submit_practice_answers(
            db, assignment_id, asserted_student_id, payload.answers
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return PracticeSubmissionResponse(
        assignment_id=assignment.id,
        status=assignment.status,
        correct_answers=sum(correct for _, correct in results),
        incorrect_answers=sum(not correct for _, correct in results),
        results=[
            PracticeResultResponse(question_index=index, is_correct=correct)
            for index, correct in results
        ],
    )


@router.post(
    "/intervention-assignments/{assignment_id}/complete",
    response_model=InterventionCompletionResponse,
)
def complete_intervention(
    assignment_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> InterventionCompletionResponse:
    assignment = _owned_assignment_or_404(db, assignment_id, asserted_student_id)
    try:
        if assignment.status != "completed":
            assignment.status = "completed"
            assignment.completed_at = datetime.now(timezone.utc)
        reassessment = generate_reassessment(db, assignment.id)
        db.commit()
    except Exception as error:
        db.rollback()
        if isinstance(error, (LookupError, PermissionError, ValueError)):
            raise HTTPException(status_code=409, detail=str(error)) from error
        raise
    db.refresh(assignment)
    return InterventionCompletionResponse(
        assignment=_assignment_response(assignment),
        reassessment=_reassessment_response(reassessment),
    )


@router.post(
    "/intervention-assignments/{assignment_id}/reassessment",
    response_model=ReassessmentResponse,
)
def get_or_create_reassessment(
    assignment_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> ReassessmentResponse:
    assignment = _owned_assignment_or_404(db, assignment_id, asserted_student_id)
    try:
        reassessment = generate_reassessment(db, assignment.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (PermissionError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _reassessment_response(reassessment)


@router.get(
    "/reassessments/{reassessment_id}",
    response_model=ReassessmentSubmissionResponse,
)
def get_reassessment_result(
    reassessment_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> ReassessmentSubmissionResponse:
    reassessment = db.scalar(
        select(Reassessment)
        .where(Reassessment.id == reassessment_id)
        .options(
            joinedload(Reassessment.intervention_assignment),
            joinedload(Reassessment.questions).joinedload(
                ReassessmentQuestion.question
            ),
            selectinload(Reassessment.results),
        )
    )
    if reassessment is None:
        raise HTTPException(status_code=404, detail="Reassessment not found")
    if reassessment.intervention_assignment.student_id != asserted_student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This reassessment does not belong to this student",
        )
    response = _reassessment_response(reassessment)
    return ReassessmentSubmissionResponse(**response.model_dump())


@router.post(
    "/reassessments/{reassessment_id}/submit",
    response_model=ReassessmentSubmissionResponse,
)
def submit_reassessment_answers(
    reassessment_id: UUID,
    payload: ReassessmentSubmissionRequest,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> ReassessmentSubmissionResponse:
    answer_map: dict[UUID, str | None] = {}
    for submitted in payload.answers:
        if submitted.question_id in answer_map:
            raise HTTPException(
                status_code=422, detail="A reassessment question may only be answered once"
            )
        answer_map[submitted.question_id] = submitted.answer
    try:
        reassessment, results = submit_reassessment(
            db,
            reassessment_id,
            answer_map,
            student_id=asserted_student_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    response = _reassessment_response(reassessment)
    return ReassessmentSubmissionResponse(
        **{k: v for k, v in response.model_dump().items() if k != "results"},
        results=[
            ReassessmentResultResponse(
                question_id=result.question_id,
                answer=result.answer,
                is_correct=result.is_correct,
            )
            for result in results
        ],
    )


@router.get(
    "/classes/{class_id}/progress",
    response_model=ClassProgressResponse,
)
def class_progress(
    class_id: UUID, db: Session = Depends(get_db)
) -> ClassProgressResponse:
    if db.get(Class, class_id) is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassProgressResponse(**get_class_progress(db, class_id))
