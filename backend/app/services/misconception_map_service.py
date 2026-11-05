"""Read-only projections over source rows. Rendering never invokes a provider."""
from datetime import datetime, timezone

from sqlalchemy import and_, case, func, or_, select

from app.models import Diagnosis, Intervention, InterventionAssignment, LearningGroup, Question, Reassessment, Student, Submission
from app.models.learning import DiagnosisCorrection
from app.services.diagnosis_service import GROUP_CONFIDENCE_THRESHOLD


def utc(value):
    # SQLite returns naive timestamps for DateTime(timezone=True); stored times are UTC.
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def current_responses(classroom):
    """One latest attempt per student/question, then latest suggestion/correction."""
    attempts = select(
        Submission.id.label('submission_id'), Submission.student_id,
        Submission.submitted_at,
        func.row_number().over(partition_by=(Submission.student_id, Submission.question_id),
            order_by=(Submission.attempt_no.desc(), Submission.submitted_at.desc(), Submission.id.desc())).label('rn'),
    ).join(Student, Student.id == Submission.student_id).join(Question, Question.id == Submission.question_id).where(
        Student.class_id == classroom.id, Question.subject == classroom.subject, Question.topic == classroom.topic,
    ).subquery()
    suggestions = (select(Diagnosis.id.label('diagnosis_id'), Diagnosis.submission_id,
        Diagnosis.misconception_code, Diagnosis.confidence, Diagnosis.evidence, Diagnosis.status,
        func.row_number().over(partition_by=Diagnosis.submission_id,
            order_by=(Diagnosis.created_at.desc(), Diagnosis.id.desc())).label('rn'))
        .where(Diagnosis.submission_id.in_(select(attempts.c.submission_id).where(attempts.c.rn == 1))).subquery())
    reviews = (select(DiagnosisCorrection.id.label('review_id'), DiagnosisCorrection.diagnosis_id,
        DiagnosisCorrection.code,
        func.row_number().over(partition_by=DiagnosisCorrection.diagnosis_id,
            order_by=DiagnosisCorrection.version.desc()).label('rn'))
        .where(DiagnosisCorrection.diagnosis_id.in_(select(suggestions.c.diagnosis_id).where(suggestions.c.rn == 1))).subquery())
    code = func.coalesce(reviews.c.code, suggestions.c.misconception_code)
    uncertain = or_(code.in_(['M06', 'FOLLOW_UP']), and_(reviews.c.review_id.is_(None),
        or_(suggestions.c.status == 'needs_followup', suggestions.c.confidence < GROUP_CONFIDENCE_THRESHOLD,
            func.length(func.trim(func.coalesce(suggestions.c.evidence, ''))) == 0)))
    return select(attempts.c.submission_id, attempts.c.student_id, attempts.c.submitted_at,
        suggestions.c.diagnosis_id, reviews.c.review_id, code.label('code'),
        case((uncertain, 1), else_=0).label('uncertain'),
    ).outerjoin(suggestions, and_(suggestions.c.submission_id == attempts.c.submission_id, suggestions.c.rn == 1)
    ).outerjoin(reviews, and_(reviews.c.diagnosis_id == suggestions.c.diagnosis_id, reviews.c.rn == 1)
    ).where(attempts.c.rn == 1).subquery()


def map_summary(db, classroom):
    rows = current_responses(classroom)
    total, start, end = db.execute(select(func.count(), func.min(rows.c.submitted_at), func.max(rows.c.submitted_at)).select_from(rows)).one()
    concepts = []
    for code, count, students, pending, uncertain in db.execute(select(rows.c.code, func.count(),
        func.count(func.distinct(rows.c.student_id)),
        func.sum(case((rows.c.review_id.is_(None), 1), else_=0)), func.sum(rows.c.uncertain)
    ).where(rows.c.diagnosis_id.is_not(None)).group_by(rows.c.code).order_by(rows.c.code)):
        concepts.append(dict(code=code, response_count=count, student_count=students,
            pending_reviews=pending, uncertain=uncertain, reviewed=count - pending))
    pending_diagnoses = total - sum(c['response_count'] for c in concepts)
    ready = db.scalar(select(func.count(func.distinct(InterventionAssignment.student_id)))
        .join(Student, Student.id == InterventionAssignment.student_id)
        .join(Intervention, Intervention.id == InterventionAssignment.intervention_id)
        .outerjoin(Reassessment, Reassessment.assignment_id == InterventionAssignment.id)
        .where(Student.class_id == classroom.id, Intervention.subject == classroom.subject,
            Intervention.topic == classroom.topic, InterventionAssignment.status == 'completed',
            or_(Reassessment.id.is_(None), Reassessment.status == 'pending'))) or 0
    return dict(class_id=classroom.id, subject=classroom.subject, topic=classroom.topic,
        queried_at=datetime.now(timezone.utc), period_from=utc(start), period_to=utc(end), total_responses=total,
        total_students=db.scalar(select(func.count(Student.id)).where(Student.class_id == classroom.id)) or 0,
        concepts=concepts, attention=dict(pending_diagnoses=pending_diagnoses,
            pending_reviews=sum(c['pending_reviews'] for c in concepts), uncertain=sum(c['uncertain'] for c in concepts),
            proposed_groups=db.scalar(select(func.count(LearningGroup.id)).where(LearningGroup.class_id == classroom.id,
                LearningGroup.topic == classroom.topic, LearningGroup.review_status == 'proposed')) or 0,
            ready_for_reassessment=ready))


def evidence_page(db, classroom, *, code=None, student_id=None, review_only=False, uncertain_only=False, limit=20, offset=0):
    rows = current_responses(classroom)
    query = select(rows).where(rows.c.diagnosis_id.is_not(None))
    if code:
        query = query.where(rows.c.code == code)
    if student_id:
        query = query.where(rows.c.student_id == student_id)
    if review_only:
        query = query.where(rows.c.review_id.is_(None))
    if uncertain_only:
        query = query.where(rows.c.uncertain == 1)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = query.order_by(rows.c.uncertain.desc(), rows.c.submitted_at.desc(), rows.c.submission_id).limit(limit).offset(offset).subquery()
    result = db.execute(select(Diagnosis, Submission, Student, Question, DiagnosisCorrection, page.c.uncertain)
        .select_from(page).join(Diagnosis, Diagnosis.id == page.c.diagnosis_id)
        .join(Submission, Submission.id == page.c.submission_id).join(Student, Student.id == Submission.student_id)
        .join(Question, Question.id == Submission.question_id)
        .outerjoin(DiagnosisCorrection, DiagnosisCorrection.id == page.c.review_id)
        .order_by(page.c.uncertain.desc(), page.c.submitted_at.desc(), page.c.submission_id))
    items = []
    for d, s, student, q, review, uncertain in result:
        items.append(dict(diagnosis_id=d.id, submission_id=s.id, student_id=student.id, student_code=student.student_code,
            question_id=q.id, question_text=q.question_text, answer=s.answer, student_explanation=s.explanation,
            submitted_at=utc(s.submitted_at), suggested_at=utc(d.created_at), original_code=d.misconception_code,
            effective_code=review.code if review else d.misconception_code, confidence=float(d.confidence),
            evidence_quote=d.evidence, ai_explanation=d.misunderstanding_explanation,
            provider=d.provider, model_version=d.model_version, uncertain=bool(uncertain),
            review=dict(code=review.code, reason=review.reason, version=review.version,
                teacher_id=review.teacher_id, created_at=utc(review.created_at)) if review else None))
    return dict(total=total, limit=limit, offset=offset, items=items)
