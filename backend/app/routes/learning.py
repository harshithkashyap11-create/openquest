from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import Class, Student, Diagnosis, Submission, LearningGroup, GroupMember
from app.models.learning import DiagnosisCorrection
from app.models.lesson import Lesson, LessonRevision, AssignedLesson
from app.schemas.learning import GenerateLesson, EditLesson, ReviewLesson, CorrectionInput, AssignLesson
from app.services.auth_service import actor_for, require_teacher
from app.services.learning_service import learner_view, record_evidence
from app.services import lesson_service
from app.services.mutation_service import replay, receipt
from app.subject_taxonomy import get_taxonomy

router = APIRouter(prefix='/api', tags=['learning intelligence'])


def owned_student(request, db, student_id, *, teacher_allowed=False):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, 'Student not found')
    actor = actor_for(request, db)
    if actor['role'] == 'teacher' and teacher_allowed:
        require_teacher(request, db, student.class_id)
    elif actor['role'] != 'student' or actor['id'] != student.id:
        raise HTTPException(403, 'STUDENT_ACCESS_DENIED')
    return student

@router.get('/students/{student_id}/learning-state')
def student_learning_state(student_id: UUID, request: Request, db=Depends(get_db)):
    owned_student(request, db, student_id, teacher_allowed=True)
    return learner_view(db, student_id)

@router.get('/classes/{class_id}/learning-states')
def class_learning_states(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    return [{'student_id': str(s.id), 'student_code': s.student_code, 'states': learner_view(db, s.id)}
        for s in db.scalars(select(Student).where(Student.class_id == class_id).order_by(Student.student_code))]

@router.get('/classes/{class_id}/lessons')
def class_lessons(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    return [lesson_service.serialize(db, item) for item in db.scalars(select(Lesson).where(Lesson.class_id == class_id).order_by(Lesson.created_at.desc(), Lesson.id))]

@router.post('/classes/{class_id}/lessons/generate', status_code=201)
def generate_lesson_draft(class_id: UUID, payload: GenerateLesson, request: Request, db=Depends(get_db)):
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise HTTPException(404, 'Class not found')
    return lesson_service.generate(db, request, classroom, payload)

@router.get('/lessons/{lesson_id}')
def lesson_detail(lesson_id: UUID, request: Request, db=Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, 'Lesson not found')
    actor = actor_for(request, db)
    if actor['role'] == 'teacher':
        require_teacher(request, db, lesson.class_id)
        return lesson_service.serialize(db, lesson)
    student = owned_student(request, db, actor['id'])
    published = db.scalar(select(LessonRevision).where(LessonRevision.lesson_id == lesson.id,
        LessonRevision.status == 'published').order_by(LessonRevision.revision_no.desc()).limit(1))
    if student.class_id != lesson.class_id or published is None:
        raise HTTPException(404, 'Published lesson not found')
    return lesson_service.serialize(db, lesson, published, student=True)

@router.patch('/lessons/{lesson_id}')
def edit_lesson(lesson_id: UUID, payload: EditLesson, request: Request, db=Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, 'Lesson not found')
    return lesson_service.edit(db, request, lesson, payload)

@router.post('/lessons/{lesson_id}/review')
def review_lesson(lesson_id: UUID, payload: ReviewLesson, request: Request, db=Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, 'Lesson not found')
    return lesson_service.review(db, request, lesson, payload)

@router.get('/students/{student_id}/lessons')
def student_lessons(student_id: UUID, request: Request, db=Depends(get_db)):
    student = owned_student(request, db, student_id)
    rows = db.execute(select(Lesson, LessonRevision).join(LessonRevision, LessonRevision.lesson_id == Lesson.id)
        .where(Lesson.class_id == student.class_id, LessonRevision.status == 'published')
        .order_by(Lesson.created_at.desc(), LessonRevision.revision_no.desc()))
    seen, result = set(), []
    for lesson, revision in rows:
        if lesson.id not in seen:
            result.append(lesson_service.serialize(db, lesson, revision, student=True))
            seen.add(lesson.id)
    return result

@router.post('/diagnoses/{diagnosis_id}/corrections')
def correct_diagnosis(diagnosis_id: UUID, payload: CorrectionInput, request: Request, db=Depends(get_db)):
    diagnosis = db.get(Diagnosis, diagnosis_id)
    if diagnosis is None:
        raise HTTPException(404, 'Diagnosis not found')
    submission = db.get(Submission, diagnosis.submission_id)
    teacher = require_teacher(request, db, submission.student.class_id)
    data, key = payload.model_dump(mode='json'), f'correction:{diagnosis_id}:{payload.request_id}'
    old = replay(db, key, data)
    if old:
        return old
    allowed = {x.code for x in get_taxonomy(submission.question.subject, submission.question.topic)} | {'CORRECT', 'FOLLOW_UP'}
    if payload.code not in allowed:
        raise HTTPException(422, 'UNSUPPORTED_MISCONCEPTION')
    version = db.scalar(select(func.max(DiagnosisCorrection.version)).where(DiagnosisCorrection.diagnosis_id == diagnosis_id)) or 0
    if version != payload.expected_version:
        raise HTTPException(409, 'STALE_CORRECTION')
    correction = DiagnosisCorrection(diagnosis_id=diagnosis_id, teacher_id=teacher, code=payload.code,
        reason=payload.reason, version=version + 1, request_id=key)
    db.add(correction)
    db.flush()
    from app.services.answer_evaluation import answers_match
    event = record_evidence(db, submission.student, submission.question.subject, submission.question.topic,
        'correction', key, {'observation_id': f'diagnosis:{diagnosis_id}', 'code': payload.code,
        'correct': answers_match(submission.answer, submission.question.correct_answer, question_text=submission.question.question_text),
        'uncertain': payload.code in {'M06', 'FOLLOW_UP'},
        'attempt': f'baseline:{submission.attempt_no}', 'question_id': str(submission.question_id),
        'teacher_id': str(teacher), 'reason': payload.reason, 'diagnosis_id': str(diagnosis_id)})
    # Invalidate unexecuted proposals after a material correction. Assigned
    # interventions remain historical records and require explicit teacher action.
    groups = db.scalars(select(LearningGroup).join(GroupMember).where(GroupMember.student_id == submission.student_id,
        LearningGroup.review_status == 'proposed', LearningGroup.topic == submission.question.topic))
    for group in groups:
        group.review_status, group.teacher_approved = 'rejected', False
    result = {'id': str(correction.id), 'diagnosis_id': str(diagnosis_id), 'code': payload.code,
        'version': correction.version, 'event_id': str(event.id)}
    receipt(db, key, data, result)
    db.commit()
    return result

@router.get('/diagnoses/{diagnosis_id}/corrections')
def diagnosis_corrections(diagnosis_id: UUID, request: Request, db=Depends(get_db)):
    diagnosis = db.get(Diagnosis, diagnosis_id)
    if diagnosis is None:
        raise HTTPException(404, 'Diagnosis not found')
    require_teacher(request, db, diagnosis.submission.student.class_id)
    return [{'id': str(c.id), 'code': c.code, 'reason': c.reason, 'version': c.version,
        'teacher_id': str(c.teacher_id), 'created_at': c.created_at.isoformat()}
        for c in db.scalars(select(DiagnosisCorrection).where(DiagnosisCorrection.diagnosis_id == diagnosis_id).order_by(DiagnosisCorrection.version))]


@router.post('/lessons/{lesson_id}/assign')
def assign_lesson(lesson_id: UUID, payload: AssignLesson, request: Request, db=Depends(get_db)):
    from app.models import Intervention, InterventionAssignment
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, 'Lesson not found')
    teacher = require_teacher(request, db, lesson.class_id)
    revision = db.get(LessonRevision, payload.revision_id)
    if revision is None or revision.lesson_id != lesson.id or revision.status != 'published':
        raise HTTPException(409, 'PUBLISHED_REVISION_REQUIRED')
    assignments = list(db.scalars(select(InterventionAssignment).join(Student).join(Intervention,
        Intervention.id == InterventionAssignment.intervention_id).where(Student.class_id == lesson.class_id,
        Intervention.subject == lesson.subject, Intervention.topic == lesson.topic,
        Intervention.misconception_code == lesson.misconception_code, InterventionAssignment.status != 'completed')))
    for assignment in assignments:
        if not db.scalar(select(AssignedLesson.id).where(AssignedLesson.assignment_id == assignment.id, AssignedLesson.revision_id == revision.id)):
            db.add(AssignedLesson(assignment_id=assignment.id, revision_id=revision.id, teacher_id=teacher))
    db.commit()
    return {'lesson_id': str(lesson.id), 'revision_id': str(revision.id), 'assignments_linked': len(assignments)}
