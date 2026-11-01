from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.models import (
    Class,
    InterventionAssignment,
    Reassessment,
    ReassessmentResult,
    Student,
)
from app.schemas.classroom import (
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
    AssessmentSummaryResponse,
    ClassAssessmentResponse,
    DemoClassResponse,
    DemoStudentResponse,
    DemoStudentResolutionRequest,
    DemoStudentResolutionResponse,
    StudentProgressResponse,
)
from app.schemas.teacher_reports import (
    AssignmentReassessmentQuestion,
    TeacherAssignmentReport,
)
from app.services.classroom_service import (
    get_assessment_summary,
    get_class_assessment,
    list_demo_classes,
    list_demo_students,
    resolve_demo_student,
    submit_student_assessment,
)
from app.services.progress_service import get_student_progress

router = APIRouter(prefix="/api", tags=["classroom"])


def _assert_demo_student(student_id: UUID, asserted_student_id: UUID) -> None:
    if student_id != asserted_student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student identity does not match the requested resource",
        )


@router.get("/demo/classes", response_model=list[DemoClassResponse])
def demo_classes(db: Session = Depends(get_db)) -> list[DemoClassResponse]:
    return list_demo_classes(db)


@router.get(
    "/demo/classes/{class_id}/students",
    response_model=list[DemoStudentResponse],
)
def demo_students(
    class_id: UUID, db: Session = Depends(get_db)
) -> list[DemoStudentResponse]:
    try:
        return list_demo_students(db, class_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/demo/students/resolve",
    response_model=DemoStudentResolutionResponse,
)
def demo_student_resolution(
    payload: DemoStudentResolutionRequest,
    db: Session = Depends(get_db),
) -> DemoStudentResolutionResponse:
    try:
        return resolve_demo_student(db, payload.class_id, payload.student_code)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/classes/{class_id}/assessment",
    response_model=ClassAssessmentResponse,
)
def class_assessment(
    class_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> ClassAssessmentResponse:
    student = db.get(Student, asserted_student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.class_id != class_id:
        raise HTTPException(
            status_code=403, detail="Student does not belong to this class"
        )
    try:
        return get_class_assessment(db, class_id, student_id=student.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/students/{student_id}/assessment-submissions",
    response_model=AssessmentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_assessment(
    student_id: UUID,
    payload: AssessmentSubmissionRequest,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> AssessmentSubmissionResponse:
    _assert_demo_student(student_id, asserted_student_id)
    try:
        return submit_student_assessment(db, student_id, payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/classes/{class_id}/assessment-summary",
    response_model=AssessmentSummaryResponse,
)
def assessment_summary(
    class_id: UUID, db: Session = Depends(get_db)
) -> AssessmentSummaryResponse:
    try:
        return get_assessment_summary(db, class_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/students/{student_id}/progress",
    response_model=StudentProgressResponse,
)
def student_progress(
    student_id: UUID,
    asserted_student_id: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
) -> StudentProgressResponse:
    _assert_demo_student(student_id, asserted_student_id)
    try:
        return StudentProgressResponse(**get_student_progress(db, student_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/classes/{class_id}/intervention-assignments",
    response_model=list[TeacherAssignmentReport],
)
def class_intervention_assignments(
    class_id: UUID,
    db: Session = Depends(get_db),
) -> list[TeacherAssignmentReport]:
    if db.get(Class, class_id) is None:
        raise HTTPException(status_code=404, detail="Class not found")
    assignments = db.scalars(
        select(InterventionAssignment)
        .join(InterventionAssignment.student)
        .where(Student.class_id == class_id)
        .options(
            joinedload(InterventionAssignment.student),
            joinedload(InterventionAssignment.intervention),
            selectinload(InterventionAssignment.reassessment).selectinload(
                Reassessment.results
            ).joinedload(ReassessmentResult.question),
        )
        .order_by(InterventionAssignment.assigned_at.desc())
    ).unique()
    reports: list[TeacherAssignmentReport] = []
    for assignment in assignments:
        reassessment = assignment.reassessment
        results = (
            [
                AssignmentReassessmentQuestion(
                    question_id=result.question_id,
                    question_text=result.question.question_text,
                    answer=result.answer,
                    is_correct=result.is_correct,
                )
                for result in reassessment.results
            ]
            if reassessment
            else []
        )
        reports.append(
            TeacherAssignmentReport(
                assignment_id=assignment.id,
                student_id=assignment.student_id,
                student_code=assignment.student.student_code,
                intervention_id=assignment.intervention_id,
                title=assignment.intervention.title,
                misconception_code=assignment.intervention.misconception_code,
                status=assignment.status,
                assigned_at=assignment.assigned_at,
                started_at=assignment.started_at,
                completed_at=assignment.completed_at,
                reassessment_status=reassessment.status if reassessment else None,
                reassessment_correct_answers=(
                    reassessment.correct_answers if reassessment else None
                ),
                reassessment_incorrect_answers=(
                    reassessment.incorrect_answers if reassessment else None
                ),
                reassessment_total_questions=(
                    reassessment.total_questions if reassessment else None
                ),
                reassessment_accuracy_percentage=(
                    reassessment.accuracy_percentage if reassessment else None
                ),
                reassessment_results=results,
            )
        )
    return reports
