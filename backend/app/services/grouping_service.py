from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Class, Diagnosis, GroupMember, LearningGroup, Submission
from app.services.diagnosis_service import GROUP_CONFIDENCE_THRESHOLD
from app.subject_taxonomy import get_taxonomy, is_follow_up_code
from app.services.diagnosis_review_service import latest_correction


def generate_proposed_groups(
    db: Session, class_id: UUID, *, topic: str | None = None
) -> list[LearningGroup]:
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise LookupError("Class not found")
    topic = topic or classroom.topic
    valid_codes = {
        item.code for item in get_taxonomy(classroom.subject, topic)
    }

    statement = (
        select(Diagnosis)
        .join(Diagnosis.submission)
        .join(Submission.student)
        .join(Submission.question)
        .where(Submission.student.has(class_id=class_id))
        .options(
            joinedload(Diagnosis.submission).joinedload(Submission.student),
            joinedload(Diagnosis.submission).joinedload(Submission.question),
        )
        .order_by(
            Diagnosis.confidence.desc(),
            Diagnosis.created_at.desc(),
            Diagnosis.id.asc(),
        )
    )
    statement = statement.where(
        Submission.question.has(subject=classroom.subject, topic=topic)
    )
    diagnoses = list(db.scalars(statement).unique())

    primary_by_student: dict[UUID, Diagnosis] = {}
    for diagnosis in diagnoses:
        student_id = diagnosis.submission.student_id
        primary_by_student.setdefault(student_id, diagnosis)

    approved_members = set(
        db.scalars(
            select(GroupMember.student_id)
            .join(GroupMember.learning_group)
            .where(
                LearningGroup.class_id == class_id,
                LearningGroup.teacher_approved.is_(True),
            )
        )
    )
    eligible_by_code: dict[str, list[Diagnosis]] = defaultdict(list)
    followup_student_ids: set[UUID] = set()
    for student_id, diagnosis in primary_by_student.items():
        if student_id in approved_members:
            continue
        correction = latest_correction(db, diagnosis.id)
        code = correction.code if correction else diagnosis.misconception_code
        if code == "CORRECT":
            continue
        if is_follow_up_code(code) or (not correction and (diagnosis.status == "needs_followup" or Decimal(diagnosis.confidence) < Decimal(
            str(GROUP_CONFIDENCE_THRESHOLD)
        ))):
            followup_student_ids.add(student_id)
            continue
        if code in valid_codes:
            eligible_by_code[code].append(diagnosis)

    existing_groups = list(
        db.scalars(
            select(LearningGroup).where(
                LearningGroup.class_id == class_id,
                LearningGroup.topic == topic,
            ).options(selectinload(LearningGroup.group_members))
        )
    )
    groups_by_code = {
        group.misconception_code: group
        for group in existing_groups
        if group.review_status == "proposed"
    }
    for group in existing_groups:
        if group.review_status != "proposed":
            continue
        desired_student_ids = {
            diagnosis.submission.student_id
            for diagnosis in eligible_by_code.get(group.misconception_code, [])
        }
        for member in list(group.group_members):
            if member.student_id not in desired_student_ids:
                db.delete(member)
        if len(desired_student_ids) < 2:
            db.delete(group)
            groups_by_code.pop(group.misconception_code, None)

    generated: list[LearningGroup] = []
    for code, diagnoses_for_code in eligible_by_code.items():
        if len(diagnoses_for_code) < 2:
            continue
        group = groups_by_code.get(code)
        if group and group.review_status != "proposed":
            continue
        if group is None:
            group = LearningGroup(
                class_id=class_id,
                topic=topic,
                misconception_code=code,
                name=f"{topic} {code} support group",
                teacher_approved=False,
                review_status="proposed",
            )
            db.add(group)
            db.flush()
        if group.teacher_approved:
            continue
        existing_member_ids = {member.student_id for member in group.group_members}
        for diagnosis in diagnoses_for_code:
            student_id = diagnosis.submission.student_id
            if student_id not in existing_member_ids:
                db.add(GroupMember(group_id=group.id, student_id=student_id))
                existing_member_ids.add(student_id)
        group.review_status = "proposed"
        generated.append(group)

    db.commit()
    for group in generated:
        db.refresh(group)
    return generated


def get_followup_student_ids(
    db: Session, class_id: UUID, *, topic: str | None = None
) -> list[UUID]:
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise LookupError("Class not found")
    topic = topic or classroom.topic
    statement = (
        select(Diagnosis)
        .join(Diagnosis.submission)
        .join(Submission.student)
        .where(
            Submission.student.has(class_id=class_id),
            Diagnosis.status == "needs_followup",
        )
        .options(joinedload(Diagnosis.submission))
    )
    statement = statement.join(Submission.question).where(
        Submission.question.has(subject=classroom.subject, topic=topic)
    )
    primary_by_student: dict[UUID, Diagnosis] = {}
    for diagnosis in db.scalars(statement).unique():
        primary_by_student.setdefault(diagnosis.submission.student_id, diagnosis)
    return [
        student_id
        for student_id, diagnosis in primary_by_student.items()
        if is_follow_up_code(diagnosis.misconception_code)
        or Decimal(diagnosis.confidence) < Decimal(
            str(GROUP_CONFIDENCE_THRESHOLD)
        )
    ]
