from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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


def _group_response(group: LearningGroup) -> LearningGroupResponse:
    return LearningGroupResponse(
        id=str(group.id),
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
    db: Session = Depends(get_db),
) -> LearningGroupResponse:
    group = db.get(LearningGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Learning group not found")
    if group.review_status != "proposed" and group.review_status != payload.status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This learning group has already been reviewed",
        )
    group.review_status = payload.status
    group.teacher_approved = payload.status == "approved"
    db.commit()
    db.refresh(group)
    return _group_response(group)
