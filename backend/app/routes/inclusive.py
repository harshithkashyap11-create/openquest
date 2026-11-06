"""Teacher-scoped inclusive learning resources."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.accessbridge.services.verification_engine import load_profiles
from app.core.database import get_db
from app.services.auth_service import require_teacher

router = APIRouter(prefix='/api', tags=['inclusive learning'])


@router.get('/classes/{class_id}/inclusive/supports')
def inclusive_supports(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    profiles = load_profiles()
    return {
        'supports': [{'id': requirement.accommodation_id, 'title': requirement.title,
                      'description': requirement.description}
                     for profile in profiles for requirement in profile.accommodation_requirements],
        'presets': [{'id': profile.profile_id, 'name': profile.teacher_visible_name,
                     'description': profile.description,
                     'support_ids': [item.accommodation_id for item in profile.accommodation_requirements]}
                    for profile in profiles],
    }


from base64 import b64decode
from binascii import Error as Base64Error
from pydantic import BaseModel, Field
from fastapi import HTTPException
from sqlalchemy import select
from app.accessbridge.services.document_parser import parse_document
from app.models.inclusive import InclusiveSource


class SourceUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1, max_length=14_000_000)


@router.post('/classes/{class_id}/inclusive/sources', status_code=201)
def inclusive_import_source(class_id: UUID, payload: SourceUpload, request: Request, db=Depends(get_db)):
    teacher_id = require_teacher(request, db, class_id)
    try:
        raw = b64decode(payload.content_base64, validate=True)
    except (ValueError, Base64Error):
        raise HTTPException(422, 'Invalid file encoding') from None
    source = parse_document(payload.filename, raw)
    item = InclusiveSource(class_id=class_id, created_by=teacher_id, source=source.model_dump(mode='json'))
    db.add(item)
    db.commit()
    return {'id': str(item.id), 'source': item.source}


@router.get('/classes/{class_id}/inclusive/sources')
def inclusive_list_sources(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    return [{'id': str(item.id), 'source': item.source} for item in db.scalars(
        select(InclusiveSource).where(InclusiveSource.class_id == class_id).order_by(InclusiveSource.created_at.desc()))]


from pydantic import ConfigDict
from app.models.inclusive import InclusiveAdaptation, InclusiveAssignment, InclusiveHistory
from app.models import Student, LearningGroup, GroupMember
from app.routes.learning import owned_student
from app.services import inclusive_learning
from app.services.diagnosis_provider import ProviderError


class AdaptationCreate(BaseModel):
    source_id: UUID
    support_ids: list[str] = Field(min_length=1, max_length=30)


class ApproveInput(BaseModel):
    version: int = Field(ge=1)
    review_note: str = Field(min_length=10, max_length=3000)


class AssignInput(BaseModel):
    student_ids: list[UUID] = Field(default_factory=list, max_length=500)
    group_ids: list[UUID] = Field(default_factory=list, max_length=100)
    whole_class: bool = False


class PracticeInput(BaseModel):
    answers: list[str] = Field(max_length=20)


def adaptation_view(item):
    return {'id': str(item.id), 'source_id': str(item.source_id), 'supports': item.supports,
            'analysis': item.analysis, 'draft': item.draft, 'findings': item.findings,
            'version': item.version, 'approved_version': item.approved_version, 'review_note': item.review_note}


def find_adaptation(db, class_id, adaptation_id):
    item = db.get(InclusiveAdaptation, adaptation_id)
    if item is None or item.class_id != class_id:
        raise HTTPException(404, 'Adaptation not found')
    return item


@router.post('/classes/{class_id}/inclusive/adaptations', status_code=201)
def inclusive_generate(class_id: UUID, payload: AdaptationCreate, request: Request, db=Depends(get_db)):
    teacher = require_teacher(request, db, class_id)
    source = db.get(InclusiveSource, payload.source_id)
    if source is None or source.class_id != class_id:
        raise HTTPException(404, 'Source not found')
    from app.core.config import get_settings
    if get_settings().auth_mode == 'required':
        from app.services.rate_limit_service import check_rate
        check_rate(('inclusive-inference', str(teacher)), 10)
    source_data = source.source
    db.commit()  # Do not hold a database transaction during the provider request.
    try:
        profile = inclusive_learning.selected_profile(payload.support_ids)
        result = inclusive_learning.generate_adaptation(source_data, profile)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except ProviderError:
        raise HTTPException(503, 'Adaptation provider unavailable; retry after checking configuration.') from None
    analysis = dict(result['analysis'])
    if result.get('bridge_draft'):
        analysis['_adapted_blocks'] = result['bridge_draft']
    item = InclusiveAdaptation(class_id=class_id, source_id=source.id, created_by=teacher,
        supports=payload.support_ids, analysis=analysis, draft=result['draft'], findings=result['findings'], version=1)
    db.add(item); db.flush()
    save_history(db, item, teacher, 'generated')
    db.commit()
    return adaptation_view(item)


@router.get('/classes/{class_id}/inclusive/adaptations')
def inclusive_adaptations(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    return [adaptation_view(item) for item in db.scalars(select(InclusiveAdaptation).where(
        InclusiveAdaptation.class_id == class_id).order_by(InclusiveAdaptation.created_at.desc()))]


@router.post('/classes/{class_id}/inclusive/adaptations/{adaptation_id}/approve')
def inclusive_approve(class_id: UUID, adaptation_id: UUID, payload: ApproveInput, request: Request, db=Depends(get_db)):
    teacher = require_teacher(request, db, class_id)
    item = find_adaptation(db, class_id, adaptation_id)
    if item.version != payload.version or not item.findings:
        raise HTTPException(409, 'Current version must be verified before approval')
    item.approved_version = item.version; item.review_note = payload.review_note
    save_history(db, item, teacher, 'approved')
    db.commit()
    return adaptation_view(item)


@router.post('/classes/{class_id}/inclusive/adaptations/{adaptation_id}/assign')
def inclusive_assign(class_id: UUID, adaptation_id: UUID, payload: AssignInput, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    item = find_adaptation(db, class_id, adaptation_id)
    if item.approved_version != item.version:
        raise HTTPException(409, 'Approve the current version before assignment')
    ids = set(payload.student_ids)
    if payload.whole_class:
        ids.update(db.scalars(select(Student.id).where(Student.class_id == class_id)))
    for group_id in payload.group_ids:
        group = db.get(LearningGroup, group_id)
        if group is None or group.class_id != class_id:
            raise HTTPException(404, 'Group not found')
        ids.update(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == group_id)))
    if not ids:
        raise HTTPException(422, 'Select at least one student')
    students = list(db.scalars(select(Student).where(Student.id.in_(ids), Student.class_id == class_id)))
    if len(students) != len(ids):
        raise HTTPException(404, 'Student not found in class')
    for student in students:
        exists = db.scalar(select(InclusiveAssignment.id).where(InclusiveAssignment.adaptation_id == item.id,
            InclusiveAssignment.student_id == student.id, InclusiveAssignment.version == item.version))
        if not exists:
            db.add(InclusiveAssignment(adaptation_id=item.id, student_id=student.id, version=item.version, content=item.draft))
    db.commit()
    return {'assigned': len(students)}


@router.get('/students/{student_id}/inclusive/lessons')
def inclusive_student_lessons(student_id: UUID, request: Request, db=Depends(get_db)):
    owned_student(request, db, student_id)
    rows = db.scalars(select(InclusiveAssignment).where(InclusiveAssignment.student_id == student_id).order_by(InclusiveAssignment.created_at.desc()))
    return [{'id': str(item.id), 'content': inclusive_learning.student_content(item.content), 'progress': item.progress} for item in rows]


@router.post('/students/{student_id}/inclusive/lessons/{inclusive_assignment_id}/practice')
def inclusive_student_practice(student_id: UUID, inclusive_assignment_id: UUID, payload: PracticeInput, request: Request, db=Depends(get_db)):
    owned_student(request, db, student_id)
    assignment = db.get(InclusiveAssignment, inclusive_assignment_id)
    if assignment is None or assignment.student_id != student_id:
        raise HTTPException(404, 'Assigned lesson not found')
    questions = assignment.content.get('questions', [])
    if len(payload.answers) != len(questions):
        raise HTTPException(422, 'Answer each question')
    from app.services.answer_evaluation import answers_match
    result = {'results': [{'correct': answers_match(answer, q['answer'], question_text=q['prompt'])}
                          for answer, q in zip(payload.answers, questions)]}
    assignment.progress = result
    db.commit()
    return result


class BlockInput(BaseModel):
    block_id: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=14000)


class QuestionInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=1000)
    hints: list[str] = Field(default_factory=list, max_length=4)


class AdaptationEdit(BaseModel):
    version: int = Field(ge=1)
    blocks: list[BlockInput] = Field(min_length=1, max_length=70)
    questions: list[QuestionInput] = Field(default_factory=list, max_length=20)


@router.patch('/classes/{class_id}/inclusive/adaptations/{adaptation_id}')
def inclusive_edit(class_id: UUID, adaptation_id: UUID, payload: AdaptationEdit, request: Request, db=Depends(get_db)):
    teacher = require_teacher(request, db, class_id)
    item = find_adaptation(db, class_id, adaptation_id)
    if item.version != payload.version:
        raise HTTPException(409, 'The adaptation changed; refresh and retry')
    import copy
    analysis = copy.deepcopy(item.analysis)
    bridge = analysis.get('_adapted_blocks')
    if not bridge or [b['block_id'] for b in bridge['blocks']] != [b.block_id for b in payload.blocks]:
        raise HTTPException(422, 'Edited blocks must match the current version in order')
    for block, changed in zip(bridge['blocks'], payload.blocks):
        block['content'] = changed.content
    bridge['version'] = item.version + 1
    bridge['narration_script'] = '\n\n'.join(block['content'] for block in bridge['blocks'])
    bridge['approval'] = None; bridge['verification'] = None; bridge['approval_status'] = 'DRAFT'
    draft = dict(item.draft)
    draft['text'] = bridge['narration_script']
    draft['blocks'] = [{'type': b.get('block_type', 'paragraph'), 'content': b['content']} for b in bridge['blocks']]
    draft['questions'] = [q.model_dump() for q in payload.questions]
    item.analysis = analysis; item.draft = draft; item.findings = []; item.approved_version = None; item.review_note = None; item.version += 1
    save_history(db, item, teacher, 'edited')
    db.commit()
    return adaptation_view(item)


@router.post('/classes/{class_id}/inclusive/adaptations/{adaptation_id}/verify')
def inclusive_verify(class_id: UUID, adaptation_id: UUID, payload: ApproveInput, request: Request, db=Depends(get_db)):
    teacher = require_teacher(request, db, class_id)
    item = find_adaptation(db, class_id, adaptation_id)
    if item.version != payload.version:
        raise HTTPException(409, 'The adaptation changed; refresh and retry')
    source = db.get(InclusiveSource, item.source_id)
    from app.core.config import get_settings
    if get_settings().auth_mode == 'required':
        from app.services.rate_limit_service import check_rate
        check_rate(('inclusive-inference', str(teacher)), 10)
    source_data, supports, analysis = source.source, item.supports, item.analysis
    db.commit()  # Release the read transaction while the independent reviewer runs.
    try:
        findings = inclusive_learning.reverify_adaptation(source_data, supports, analysis, analysis['_adapted_blocks'])
    except (ValueError, KeyError, ProviderError):
        raise HTTPException(503, 'Verification unavailable; review remains required. Retry verification.') from None
    item.findings = findings; item.approved_version = None; item.review_note = None
    save_history(db, item, teacher, 'verified')
    db.commit()
    return adaptation_view(item)


class ExistingLessonInput(BaseModel):
    lesson_id: UUID


@router.post('/classes/{class_id}/inclusive/sources/from-lesson', status_code=201)
def inclusive_source_from_lesson(class_id: UUID, payload: ExistingLessonInput, request: Request, db=Depends(get_db)):
    from app.models.lesson import Lesson, LessonRevision
    teacher = require_teacher(request, db, class_id)
    lesson = db.get(Lesson, payload.lesson_id)
    if not lesson or lesson.class_id != class_id:
        raise HTTPException(404, 'Lesson not found')
    revision = db.scalar(select(LessonRevision).where(LessonRevision.lesson_id == lesson.id).order_by(LessonRevision.revision_no.desc()).limit(1))
    if not revision or revision.language != 'en':
        raise HTTPException(422, 'Select an English lesson')
    content = revision.content
    parts = [content['title'], 'Learning Objectives:', '\n'.join(content['objectives']),
             'Explanation:', content['explanation'], 'Correction:', content['misconception_correction'],
             'Worked example:', content['worked_example']['problem'], '\n'.join(content['worked_example']['steps']),
             'Solution: ' + content['worked_example']['answer'], 'Questions:',
             '\n'.join(q['prompt'] for q in content['practice_questions']), content['exit_ticket']['prompt']]
    source = parse_document('classpulse-lesson.txt', '\n\n'.join(parts).encode())
    item = InclusiveSource(class_id=class_id, created_by=teacher, source=source.model_dump(mode='json'))
    db.add(item); db.commit()
    return {'id': str(item.id), 'source': item.source}


@router.get('/classes/{class_id}/inclusive/audience')
def inclusive_audience(class_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    students = db.scalars(select(Student).where(Student.class_id == class_id).order_by(Student.student_code))
    groups = db.scalars(select(LearningGroup).where(LearningGroup.class_id == class_id).order_by(LearningGroup.name))
    return {'students': [{'id': str(s.id), 'name': s.student_code} for s in students],
            'groups': [{'id': str(g.id), 'name': g.name} for g in groups]}


@router.get('/classes/{class_id}/inclusive/adaptations/{adaptation_id}/export/{format_name}')
def inclusive_export(class_id: UUID, adaptation_id: UUID, format_name: str, request: Request, db=Depends(get_db)):
    from html import escape
    from fastapi.responses import Response
    require_teacher(request, db, class_id)
    item = find_adaptation(db, class_id, adaptation_id)
    content = item.draft
    status = 'APPROVED' if item.approved_version == item.version else 'DRAFT — NOT APPROVED'
    plain = '\n\n'.join([status, content['title'], *content.get('objectives', []), content['text'], *[q['prompt'] for q in content.get('questions', [])]])
    if format_name == 'html':
        body = f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{escape(content["title"])}</title><main><p>{escape(status)}</p><h1>{escape(content["title"])}</h1>'
        body += '<h2>Learning objectives</h2><ul>' + ''.join(f'<li>{escape(o)}</li>' for o in content.get('objectives', [])) + '</ul>'
        blocks = content.get('blocks') or [{'type': 'paragraph', 'content': p} for p in content['text'].split('\n\n')]
        body += ''.join(f'<h2>{escape(b["content"])}</h2>' if b['type'] == 'heading' else f'<p>{escape(b["content"])}</p>' for b in blocks)
        body += ''.join(f'<p>{escape(q["prompt"])}</p>' for q in content.get('questions', [])) + '</main></html>'
        return Response(body, media_type='text/html', headers={'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'"})
    if format_name == 'txt':
        return Response(plain, media_type='text/plain; charset=utf-8')
    if format_name == 'ssml':
        return Response('<speak xml:lang="en">' + ''.join(f'<p>{escape(part)}</p>' for part in plain.split('\n\n')) + '</speak>', media_type='application/ssml+xml')
    if format_name == 'report':
        return {'version': item.version, 'status': status, 'findings': item.findings, 'review_note': item.review_note,
                'limitations': 'Automated checks are review aids and do not certify accessibility.'}
    if format_name == 'pdf':
        import io
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        output = io.BytesIO(); styles = getSampleStyleSheet()
        story = [Paragraph(escape(part).replace('\n', '<br/>'), styles['BodyText']) for part in plain.split('\n\n')]
        SimpleDocTemplate(output).build([piece for para in story for piece in (para, Spacer(1, 12))])
        return Response(output.getvalue(), media_type='application/pdf')
    raise HTTPException(404, 'Export format not found')


def save_history(db, item, teacher, action):
    import copy
    db.add(InclusiveHistory(adaptation_id=item.id, actor_id=teacher, action=action, version=item.version,
                            snapshot=copy.deepcopy(adaptation_view(item))))


@router.get('/classes/{class_id}/inclusive/adaptations/{adaptation_id}/history')
def inclusive_history(class_id: UUID, adaptation_id: UUID, request: Request, db=Depends(get_db)):
    require_teacher(request, db, class_id)
    item = find_adaptation(db, class_id, adaptation_id)
    rows = db.scalars(select(InclusiveHistory).where(InclusiveHistory.adaptation_id == item.id).order_by(InclusiveHistory.id))
    return [{'action': row.action, 'version': row.version, 'snapshot': row.snapshot, 'created_at': row.created_at.isoformat()} for row in rows]
