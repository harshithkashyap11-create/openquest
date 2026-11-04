from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, object_session

from app.core.database import get_db
from app.models import Diagnosis, Submission
from app.schemas.diagnosis import (
    DiagnosisBatchResponse,
    DiagnosisItem,
    DiagnosisSummary,
)
from app.services.diagnosis_provider import ProviderError
from app.services.diagnosis_service import (
    MAX_DIAGNOSIS_BATCH_SIZE,
    DiagnosisService,
)

router = APIRouter(prefix="/api", tags=["diagnoses"])


def _diagnosis_item(diagnosis: Diagnosis) -> DiagnosisItem:
    submission = diagnosis.submission
    from app.services.diagnosis_review_service import latest_correction
    correction = latest_correction(object_session(diagnosis), diagnosis.id)
    return DiagnosisItem(
        id=str(diagnosis.id),
        effective_code=correction.code if correction else diagnosis.misconception_code,
        correction_version=correction.version if correction else 0,
        submission_id=str(submission.id),
        student_id=str(submission.student_id),
        student_code=submission.student.student_code,
        misconception_code=diagnosis.misconception_code,
        subject=submission.question.subject,
        topic=submission.question.topic,
        confidence=float(diagnosis.confidence),
        evidence=diagnosis.evidence,
        misconception_description=diagnosis.misconception_description or "",
        misunderstanding_explanation=diagnosis.misunderstanding_explanation or "",
        suggested_intervention=diagnosis.suggested_intervention or "",
        needs_followup=diagnosis.status == "needs_followup",
        followup_question=diagnosis.followup_question,
        provider=diagnosis.provider,
        status=diagnosis.status,
        model_version=diagnosis.model_version,
    )


@router.post(
    "/classes/{class_id}/diagnose",
    response_model=DiagnosisBatchResponse,
)
def diagnose_pending_submissions(
    class_id: UUID,
    limit: int = Query(default=MAX_DIAGNOSIS_BATCH_SIZE, ge=1, le=MAX_DIAGNOSIS_BATCH_SIZE),
    db: Session = Depends(get_db),
) -> DiagnosisBatchResponse:
    try:
        result = DiagnosisService(db).diagnose_class(class_id, limit=limit)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (ProviderError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    if result.failed and not result.diagnosed:
        if result.rate_limited == result.failed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"message": "OpenRouter rate limit exceeded", "errors": result.errors},
                headers={"Retry-After": "30"},
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "No submissions were diagnosed", "errors": result.errors},
        )
    return DiagnosisBatchResponse(
        diagnosed=result.diagnosed,
        failed=result.failed,
        timed_out=result.timed_out,
        rate_limited=result.rate_limited,
        remaining_pending=result.remaining_pending,
        diagnoses=[_diagnosis_item(item) for item in result.diagnoses],
        errors=result.errors,
    )


@router.get(
    "/classes/{class_id}/diagnoses",
    response_model=list[DiagnosisItem],
)
def list_diagnoses(
    class_id: UUID,
    code: str | None = None,
    followup_only: bool = False,
    student_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DiagnosisItem]:
    statement = (
        select(Diagnosis)
        .join(Diagnosis.submission)
        .where(Submission.student.has(class_id=class_id))
        .options(
            joinedload(Diagnosis.submission).joinedload(Submission.student),
            joinedload(Diagnosis.submission).joinedload(Submission.question),
        )
        .order_by(Diagnosis.created_at.desc())
    )
    if code:
        statement = statement.where(Diagnosis.misconception_code == code.upper())
    if followup_only:
        statement = statement.where(Diagnosis.status == "needs_followup")
    if student_id:
        statement = statement.where(Submission.student_id == student_id)
    diagnoses = db.scalars(statement.limit(limit).offset(offset)).unique()
    return [_diagnosis_item(diagnosis) for diagnosis in diagnoses]


@router.get(
    "/classes/{class_id}/diagnoses/summary",
    response_model=DiagnosisSummary,
)
def diagnosis_summary(
    class_id: UUID, db: Session = Depends(get_db)
) -> DiagnosisSummary:
    rows = db.execute(
        select(Diagnosis.misconception_code, func.count(Diagnosis.id))
        .join(Diagnosis.submission)
        .where(Submission.student.has(class_id=class_id))
        .group_by(Diagnosis.misconception_code)
    )
    by_code = {code: count for code, count in rows}
    total = sum(by_code.values())
    followup_count = db.scalar(
        select(func.count(Diagnosis.id))
        .join(Diagnosis.submission)
        .where(
            Submission.student.has(class_id=class_id),
            Diagnosis.status == "needs_followup",
        )
    ) or 0
    return DiagnosisSummary(
        total_diagnoses=total,
        by_code=by_code,
        correct_count=by_code.get("CORRECT", 0),
        followup_count=followup_count,
    )
