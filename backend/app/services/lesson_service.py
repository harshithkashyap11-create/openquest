"""Structured lesson generation; review and publication are teacher-only actions."""
import json
from fastapi import HTTPException
from sqlalchemy import select, func
from pydantic import ValidationError
from app.core.config import get_settings
from app.models.lesson import Lesson, LessonRevision, LessonReview
from app.models import Student
from app.models.learning import LearningEvent, LearnerState
from app.schemas.learning import LessonContent
from app.services.auth_service import require_teacher
from app.services.diagnosis_provider import ProviderError
from app.services.intervention_service import INTERVENTION_TEMPLATES
from app.services.mutation_service import replay, receipt
from app.subject_taxonomy import get_taxonomy


def configured_chat():
    settings = get_settings()
    if settings.ai_provider == 'gemini':
        from app.services.gemini_client import GeminiChatClient
        return GeminiChatClient.from_settings(settings), 'gemini', settings.gemini_model
    if settings.ai_provider == 'openrouter':
        from app.services.openrouter_client import OpenRouterChatClient
        return OpenRouterChatClient(api_key=settings.openrouter_api_key or '', model=settings.openrouter_model or '',
            base_url=settings.openrouter_base_url, timeout_seconds=settings.openrouter_timeout_seconds), 'openrouter', settings.openrouter_model
    return None, 'template', None


def template_content(code, language):
    template = INTERVENTION_TEMPLATES.get(code)
    if not template:
        raise ProviderError('No safe template for this misconception')
    content = {'title': template.title, 'objectives': [template.learning_objective],
        'misconception_correction': template.explanation,
        'explanation': template.explanation, 'worked_example': {'problem': template.guided_example.get('question', template.title),
        'steps': [template.guided_example.get('steps', template.explanation)],
        'answer': template.guided_example.get('answer', 'Discuss the worked example with your teacher.')},
        'practice_questions': [{'prompt': q, 'answer': a, 'hints': [h]} for q, a, h in zip(template.practice_questions, template.expected_answers, template.hints)],
        'exit_ticket': {'prompt': template.practice_questions[-1], 'answer': template.expected_answers[-1], 'hints': [template.hints[-1]]}}
    if language != 'en':
        if code != 'M01':
            raise ProviderError('A reviewed regional-language template is unavailable for this topic; use live generation or English.')
        local = {
            'hi': ['समान भागों में भिन्नों को जोड़ें', 'समान हर का उपयोग करके भिन्नों को जोड़ना सीखें।',
                'अंश और हर को अलग-अलग नहीं जोड़ते। पहले दोनों भिन्नों को समान हर में लिखें। फिर अंशों को जोड़ें और हर वही रखें।',
                'हर 12 लें: 1/3 = 4/12 और 1/4 = 3/12। अंश जोड़ें: 4 + 3 = 7।', 'पहले समान हर बनाइए।'],
            'te': ['సమాన భాగాలతో భిన్నాలను కూడండి', 'సమాన హారంతో భిన్నాలను కూడటం నేర్చుకోండి.',
                'లవాలను, హారాలను విడివిడిగా కూడకూడదు. మొదట రెండు భిన్నాలను సమాన హారంతో రాయండి. తరువాత లవాలను కూడి, హారాన్ని అలాగే ఉంచండి.',
                'హారం 12 తీసుకోండి: 1/3 = 4/12 మరియు 1/4 = 3/12. లవాలను కూడండి: 4 + 3 = 7.', 'మొదట సమాన హారాన్ని కనుగొనండి.'],
        }[language]
        content.update(title=local[0], objectives=[local[1]], explanation=local[2],
            misconception_correction=local[2],
            worked_example={'problem': '1/3 + 1/4', 'steps': [local[3]], 'answer': '7/12'},
            practice_questions=[{'prompt': q, 'answer': a, 'hints': [local[4]]} for q, a in [('1/2 + 1/3', '5/6'), ('2/3 + 1/6', '5/6'), ('1/4 + 1/2', '3/4')]],
            exit_ticket={'prompt': '1/5 + 1/10', 'answer': '3/10', 'hints': [local[4]]})
    return LessonContent.model_validate(content).model_dump()


def generate(db, request, classroom, payload):
    teacher = require_teacher(request, db, classroom.id)
    data = payload.model_dump(mode='json')
    key = f'lesson:{classroom.id}:{payload.request_id}'
    old = replay(db, key, data)
    if old:
        return old
    if payload.misconception_code not in {t.code for t in get_taxonomy(classroom.subject, classroom.topic)} or payload.misconception_code not in INTERVENTION_TEMPLATES:
        raise HTTPException(422, 'UNSUPPORTED_MISCONCEPTION')
    context = {'subject': classroom.subject, 'topic': classroom.topic, 'misconception_code': payload.misconception_code, 'language': payload.language}
    target = next(t for t in get_taxonomy(classroom.subject, classroom.topic) if t.code == payload.misconception_code)
    context.update(misconception_description=target.description, learning_objective=INTERVENTION_TEMPLATES[payload.misconception_code].learning_objective)
    evidence = list(db.scalars(select(LearningEvent).join(Student, Student.id == LearningEvent.student_id).where(
        Student.class_id == classroom.id, LearningEvent.subject == classroom.subject,
        LearningEvent.topic == classroom.topic, LearningEvent.kind.in_(['diagnosis', 'correction', 'reassessment']))
        .order_by(LearningEvent.created_at.desc()).limit(20)))
    context.update(difficulty=payload.difficulty, duration_minutes=payload.duration_minutes,
        enrolled_students=db.scalar(select(func.count(Student.id)).where(Student.class_id == classroom.id)),
        evidence_ids=[str(e.id) for e in evidence],
        supported_gap_observations=sum(e.data.get('code') == payload.misconception_code for e in evidence),
        evidence_note='Recent saved observations; not a calibrated learning assessment.' if evidence else 'No recorded learner evidence; teacher-selected topic draft.')
    # End read transaction before the external request; no learner identity sent.
    db.commit()
    try:
        client, provider, model = configured_chat()
        if client:
            prompt = ('Create an age-appropriate school lesson for the following trusted context. '
                'Write all teaching prose in the requested language (en English, hi Hindi, te Telugu). Preserve mathematics, units, and English grammar examples. '
                'Return ONLY JSON matching the schema. Include valid answer keys, a distinct exit ticket and meaningful hints. '
                'Every example, practice question and exit ticket must target the specified misconception and learning objective; a general topic introduction is insufficient. '
                'Explain the mistaken rule and its replacement in misconception_correction. '
                'Use plain text math such as 1/2 and ×. Never use LaTeX, dollar delimiters or HTML. '
                'Use this verified analogous instructional example as a guide: ' + json.dumps(INTERVENTION_TEMPLATES[payload.misconception_code].guided_example, ensure_ascii=False) + '\n'
                'No student identities, personal data or unsupported claims. Content is a draft requiring teacher review.\n'
                + json.dumps({k: v for k, v in context.items() if k != 'evidence_ids'}, ensure_ascii=False) + '\nSchema: ' + json.dumps(LessonContent.model_json_schema()))
            content = LessonContent.model_validate_json(client.complete_json(prompt=prompt, temperature=0.2)).model_dump()
            context['requested_model'] = model
            context['generation_latency_ms'] = getattr(client, 'latency_ms', None)
            model = getattr(client, 'reported_model', None) or model
            note = 'Live provider draft; answer keys and language require teacher review.'
        else:
            content = template_content(payload.misconception_code, payload.language)
            note = 'Deterministic teaching template; no live inference. Teacher review required.'
    except (ProviderError, ValidationError):
        if not payload.allow_fallback:
            raise HTTPException(503, 'LESSON_PROVIDER_UNAVAILABLE: retry or explicitly request a labeled template')
        content = template_content(payload.misconception_code, payload.language)
        provider, model, note = 'template', None, 'Explicit fallback after provider failure; no live inference.'
    lesson = Lesson(class_id=classroom.id, subject=classroom.subject, topic=classroom.topic,
        misconception_code=payload.misconception_code, created_by=teacher, generation_context=context)
    db.add(lesson)
    db.flush()
    revision = LessonRevision(lesson_id=lesson.id, revision_no=1, language=payload.language,
        content=content, provider=provider, model=model, generation_note=note)
    db.add(revision)
    db.flush()
    result = serialize(db, lesson, revision)
    receipt(db, key, data, result)
    db.commit()
    return result


def latest(db, lesson_id):
    return db.scalar(select(LessonRevision).where(LessonRevision.lesson_id == lesson_id).order_by(LessonRevision.revision_no.desc()).limit(1))


def serialize(db, lesson, revision=None, *, student=False):
    revision = revision or latest(db, lesson.id)
    content = json.loads(json.dumps(revision.content))
    if student:
        for question in [*content['practice_questions'], content['exit_ticket']]:
            question.pop('answer', None)
    reviews = list(db.scalars(select(LessonReview).where(LessonReview.revision_id == revision.id).order_by(LessonReview.created_at)))
    return {'id': str(lesson.id), 'class_id': str(lesson.class_id), 'subject': lesson.subject, 'topic': lesson.topic,
        'generation_context': {k: v for k, v in lesson.generation_context.items() if not student or k != 'evidence_ids'},
        'misconception_code': lesson.misconception_code, 'revision': {'id': str(revision.id), 'number': revision.revision_no,
        'language': revision.language, 'status': revision.status, 'content': content, 'provider': revision.provider,
        'model': revision.model, 'generation_note': revision.generation_note,
        'reviews': [{'action': r.action, 'teacher_id': str(r.teacher_id), 'created_at': r.created_at.isoformat(), **r.notes} for r in reviews]}}


def edit(db, request, lesson, payload):
    teacher = require_teacher(request, db, lesson.class_id)
    old = latest(db, lesson.id)
    if old.id != payload.revision_id:
        raise HTTPException(409, 'STALE_REVISION')
    revision = LessonRevision(lesson_id=lesson.id, revision_no=old.revision_no + 1,
        language=old.language, content=payload.content.model_dump(), provider=old.provider,
        model=old.model, generation_note=f'Teacher edited revision {old.revision_no}; prior provenance retained; new review required.')
    db.add(revision)
    db.flush()
    db.add(LessonReview(revision_id=revision.id, teacher_id=teacher, action='edit', notes={'prior_revision': str(old.id)}))
    db.commit()
    return serialize(db, lesson, revision)


def review(db, request, lesson, payload):
    teacher = require_teacher(request, db, lesson.class_id)
    revision = latest(db, lesson.id)
    if revision.id != payload.revision_id:
        raise HTTPException(409, 'STALE_REVISION')
    targets = {'approve': 'approved', 'reject': 'rejected', 'publish': 'published', 'archive': 'archived'}
    target = targets[payload.action]
    if revision.status == target:
        return serialize(db, lesson, revision)
    allowed = {'draft': {'approved', 'rejected'}, 'approved': {'published', 'rejected'}, 'published': {'archived'}}
    if target not in allowed.get(revision.status, set()):
        raise HTTPException(409, 'INVALID_LESSON_TRANSITION')
    LessonContent.model_validate(revision.content)
    if payload.action == 'approve' and not (payload.answer_keys_reviewed and payload.language_reviewed):
        raise HTTPException(422, 'ANSWER_KEY_AND_LANGUAGE_REVIEW_REQUIRED')
    revision.status = target
    if target == 'published':
        for previous in db.scalars(select(LessonRevision).where(LessonRevision.lesson_id == lesson.id,
                LessonRevision.status == 'published', LessonRevision.id != revision.id)):
            previous.status = 'archived'
            db.add(LessonReview(revision_id=previous.id, teacher_id=teacher, action='superseded', notes={'new_revision': str(revision.id)}))
    db.add(LessonReview(revision_id=revision.id, teacher_id=teacher, action=payload.action,
        notes={'reason': payload.reason, 'answer_keys_reviewed': payload.answer_keys_reviewed, 'language_reviewed': payload.language_reviewed}))
    db.commit()
    return serialize(db, lesson, revision)
