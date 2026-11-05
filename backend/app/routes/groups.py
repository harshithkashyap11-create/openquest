from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import GroupMember, LearningGroup
from app.schemas.groups import (
    GroupGenerationResponse,
    GroupMemberResponse,
    GroupReviewRequest,
    LearningGroupResponse,
)
from app.services.grouping_service import (
    generate_proposed_groups,
    get_followup_student_ids,
)

router = APIRouter(prefix="/api", tags=["groups"])


def _group_revision(group):
    from app.services.mutation_service import fingerprint
    return fingerprint({'id': str(group.id), 'code': group.misconception_code, 'topic': group.topic,
        'members': sorted(str(m.student_id) for m in group.group_members)})


def _group_response(group: LearningGroup) -> LearningGroupResponse:
    return LearningGroupResponse(
        id=str(group.id),
        revision=_group_revision(group),
        class_id=str(group.class_id),
        topic=group.topic,
        misconception_code=group.misconception_code,
        name=group.name,
        review_status=group.review_status,
        teacher_approved=group.teacher_approved,
        members=[
            GroupMemberResponse(
                student_id=str(member.student_id),
                student_code=member.student.student_code,
            )
            for member in group.group_members
        ],
    )


@router.post(
    "/classes/{class_id}/groups/generate",
    response_model=GroupGenerationResponse,
)
def generate_groups(
    class_id: UUID, db: Session = Depends(get_db)
) -> GroupGenerationResponse:
    try:
        groups = generate_proposed_groups(db, class_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return GroupGenerationResponse(
        groups=[_group_response(group) for group in groups],
        followup_student_ids=[
            str(student_id) for student_id in get_followup_student_ids(db, class_id)
        ],
    )


@router.get(
    "/classes/{class_id}/groups",
    response_model=list[LearningGroupResponse],
)
def list_groups(
    class_id: UUID, db: Session = Depends(get_db)
) -> list[LearningGroupResponse]:
    groups = db.scalars(
        select(LearningGroup)
        .where(LearningGroup.class_id == class_id)
        .options(
            joinedload(LearningGroup.group_members).joinedload(GroupMember.student)
        )
        .order_by(LearningGroup.created_at)
    ).unique()
    return [_group_response(group) for group in groups]


@router.patch(
    "/groups/{group_id}/review",
    response_model=LearningGroupResponse,
)
def review_group(
    group_id: UUID,
    payload: GroupReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LearningGroupResponse:
    group = db.get(LearningGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Learning group not found")
    from app.core.config import get_settings
    from app.services.auth_service import require_teacher
    from app.services.learning_service import record_evidence
    teacher_id = require_teacher(request, db, group.class_id)
    # A foreign key proves existence, not class membership. Recheck persisted
    # proposal members before recording a decision or creating student events.
    if payload.status == 'approved' and (len(group.group_members) < 2 or any(
        member.student.class_id != group.class_id for member in group.group_members
    )):
        raise HTTPException(409, 'INVALID_GROUP_MEMBERSHIP')
    revision = _group_revision(group)
    if (payload.expected_revision is not None and payload.expected_revision != revision) or (get_settings().auth_mode == 'required' and payload.expected_revision is None):
        raise HTTPException(409, 'STALE_GROUP_RECOMMENDATION: refresh before reviewing')
    if group.review_status != "proposed" and group.review_status != payload.status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This learning group has already been reviewed",
        )
    group.review_status = payload.status
    group.teacher_approved = payload.status == "approved"
    for member in group.group_members:
        record_evidence(db, member.student, group.classroom.subject, group.topic,
            'teacher_review', f'group-review:{group.id}:{revision}:{payload.status}:{member.student_id}', {
                'group_id': str(group.id), 'reviewed_revision': revision, 'outcome': payload.status,
                'teacher_id': str(teacher_id), 'code': group.misconception_code})
    db.commit()
    db.refresh(group)
    return _group_response(group)
