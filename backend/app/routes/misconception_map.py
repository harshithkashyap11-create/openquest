from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.database import get_db
from app.models import Class
from app.routes.learning import owned_student
from app.schemas.misconception_map import EvidencePage, JourneyPage, MapSummary
from app.services.auth_service import require_teacher
from app.services.journey_service import student_journey
from app.services.misconception_map_service import evidence_page, map_summary
from app.subject_taxonomy import all_misconception_codes

router = APIRouter(prefix='/api', tags=['misconception map'])


@router.get('/classes/{class_id}/misconception-map', response_model=MapSummary)
def classroom_map(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    return map_summary(db, db.get(Class, class_id))


@router.get('/classes/{class_id}/misconception-map/evidence', response_model=EvidencePage)
def map_evidence(class_id: UUID, request: Request, code: str | None = Query(default=None, max_length=40),
    student_id: UUID | None = None, review_only: bool = False, uncertain_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0), db=Depends(get_db)):
    require_teacher(request, db, class_id)
    if code and code not in all_misconception_codes():
        raise HTTPException(422, 'UNSUPPORTED_MISCONCEPTION')
    return evidence_page(db, db.get(Class, class_id), code=code, student_id=student_id,
        review_only=review_only, uncertain_only=uncertain_only, limit=limit, offset=offset)


@router.get('/students/{student_id}/journey', response_model=JourneyPage)
def learning_journey(student_id: UUID, request: Request,
    limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0), db=Depends(get_db)):
    student = owned_student(request, db, student_id, teacher_allowed=True)
    return student_journey(db, student, limit=limit, offset=offset)
