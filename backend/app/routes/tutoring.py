"""Assignment-bound guided practice. No hint endpoint accepts assessment items."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from app.core.database import get_db
from app.models.learning import LearningEvent
from app.schemas.learning import HintRequest
from app.services.auth_service import actor_for
from app.services.intervention_assignment_service import get_owned_assignment
from app.services.intervention_service import INTERVENTION_TEMPLATES
from app.services.learning_service import record_evidence
from app.services.mutation_service import replay, receipt
from app.schemas.interventions import PracticeAnswer
from app.schemas.learning import StrictInput
from pydantic import Field

class OfflinePractice(StrictInput):
    request_id: str = Field(min_length=8, max_length=100)
    intervention_id: UUID
    answers: list[PracticeAnswer] = Field(min_length=1, max_length=20)

router = APIRouter(prefix='/api', tags=['adaptive guided tutor'])

@router.post('/intervention-assignments/{assignment_id}/sync-practice')
def sync_practice(assignment_id: UUID, payload: OfflinePractice, request: Request, db=Depends(get_db)):
    from app.services.intervention_assignment_service import submit_practice_answers
    assignment = owned(request, db, assignment_id)
    key, data = f'sync-practice:{assignment.id}:{payload.request_id}', payload.model_dump(mode='json')
    old = replay(db, key, data)
    if old:
        return old
    if assignment.intervention_id != payload.intervention_id or assignment.status == 'completed':
        raise HTTPException(409, 'OFFLINE_CONTENT_CONFLICT: download the current activity; local answers remain on this device')
    try:
        _, results = submit_practice_answers(db, assignment.id, assignment.student_id, payload.answers, commit=False)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    result = {'assignment_id': str(assignment.id), 'request_id': payload.request_id,
        'status': 'synchronized', 'results': [{'question_index': i, 'is_correct': correct} for i, correct in results]}
    receipt(db, key, data, result)
    db.commit()
    return result


def owned(request, db, assignment_id):
    actor = actor_for(request, db)
    if actor['role'] != 'student' or not actor['id']:
        raise HTTPException(403, 'STUDENT_ROLE_REQUIRED')
    try:
        return get_owned_assignment(db, assignment_id, actor['id'])
    except LookupError as error:
        raise HTTPException(404, 'Assignment not found') from error
    except PermissionError as error:
        raise HTTPException(403, 'STUDENT_ACCESS_DENIED') from error


def history(db, assignment):
    return [e for e in db.scalars(select(LearningEvent).where(LearningEvent.student_id == assignment.student_id,
        LearningEvent.kind == 'hint').order_by(LearningEvent.created_at, LearningEvent.id))
        if e.data.get('assignment_id') == str(assignment.id)]


def ladder(assignment, index, language):
    template = INTERVENTION_TEMPLATES[assignment.intervention.misconception_code]
    if language == 'en':
        return [f'Think about the idea: {template.learning_objective}',
            template.instructions,
            template.hints[min(index, len(template.hints) - 1)],
            f'Use an analogous example: {template.guided_example["question"]} {template.guided_example["steps"]} Now write the first step for your own question.']
    if assignment.intervention.misconception_code != 'M01':
        raise HTTPException(422, 'REGIONAL_HINT_UNAVAILABLE: use an approved translated lesson or English hints')
    return {
        'hi': ['हर समान आकार के भाग बताता है। क्या दोनों भिन्नों के भाग समान हैं?',
            'पहले समान हर लें। अंश और हर को एक ही संख्या से गुणा करके समतुल्य भिन्न बनाइए।',
            'दोनों हरों का एक साझा गुणज लिखिए। फिर हर भिन्न को उस हर में बदलने के लिए आवश्यक गुणक लिखिए।',
            'उदाहरण: 1/3 + 1/4 के लिए हर 12 लें। 1/3 = 4/12 और 1/4 = 3/12। अपने सवाल में इसी तरह पहले दो समतुल्य भिन्न लिखिए।'],
        'te': ['హారం సమాన పరిమాణం గల భాగాలను సూచిస్తుంది. రెండు భిన్నాల్లో భాగాల పరిమాణం ఒకటేనా?',
            'మొదట సమాన హారాన్ని తీసుకోండి. లవాన్ని, హారాన్ని ఒకే సంఖ్యతో గుణించి సమాన భిన్నాలను రాయండి.',
            'రెండు హారాల ఉమ్మడి గుణిజాన్ని రాయండి. ప్రతి భిన్నాన్ని ఆ హారానికి మార్చేందుకు అవసరమైన గుణకాన్ని కనుగొనండి.',
            'ఉదాహరణ: 1/3 + 1/4 కోసం హారం 12 తీసుకోండి. 1/3 = 4/12 మరియు 1/4 = 3/12. మీ ప్రశ్నకు కూడా మొదట సమాన హారం గల రెండు భిన్నాలను రాయండి.'],
    }[language]

@router.get('/intervention-assignments/{assignment_id}/tutor')
def tutor_history(assignment_id: UUID, request: Request, db=Depends(get_db)):
    assignment = owned(request, db, assignment_id)
    from app.models.lesson import AssignedLesson, LessonRevision, Lesson
    from app.services.lesson_service import serialize
    links = db.scalars(select(AssignedLesson).where(AssignedLesson.assignment_id == assignment.id))
    lessons = []
    for link in links:
        revision = db.get(LessonRevision, link.revision_id)
        lessons.append(serialize(db, db.get(Lesson, revision.lesson_id), revision, student=True))
    return {'assignment_id': str(assignment.id), 'policy': 'guided_practice', 'max_hint_level': 4,
        'lessons': lessons,
        'events': [e.data for e in history(db, assignment)]}

@router.post('/intervention-assignments/{assignment_id}/tutor/hints')
def request_hint(assignment_id: UUID, payload: HintRequest, request: Request, db=Depends(get_db)):
    assignment = owned(request, db, assignment_id)
    key, data = f'hint:{assignment.id}:{payload.request_id}', payload.model_dump(mode='json')
    previous = replay(db, key, data)
    if previous:
        return previous
    if assignment.status == 'completed':
        raise HTTPException(409, 'ASSESSMENT_PROTECTED: tutoring ends when reassessment becomes available')
    if payload.question_index >= len(assignment.intervention.practice_questions):
        raise HTTPException(422, 'QUESTION_OUT_OF_RANGE')
    events = [e for e in history(db, assignment) if e.data['question_index'] == payload.question_index]
    level = len(events) + 1
    if level > 4:
        raise HTTPException(409, 'HINTS_EXHAUSTED: try the practice question or ask your teacher')
    if events and not payload.response.strip():
        raise HTTPException(422, 'RESPONSE_REQUIRED: describe what you tried before the next hint')
    generated = None
    if payload.generation_mode == 'live':
        from app.services.adaptive_tutor_service import live_hint
        from app.services.diagnosis_provider import ProviderError
        from app.services.rate_limit_service import check_rate
        check_rate(('live-tutor', str(assignment.student_id)), 10)
        db.commit()  # release read transaction before external inference
        try:
            generated = live_hint(assignment, payload.question_index, level, payload.language,
                payload.response, [e.data['hint'] for e in events])
        except ProviderError as error:
            raise HTTPException(503, 'TUTOR_UNAVAILABLE: your practice is saved; retry or select labeled template hints') from error
    hints = None if generated else ladder(assignment, payload.question_index, payload.language)
    result = {'assignment_id': str(assignment.id), 'question_index': payload.question_index,
        'question': assignment.intervention.practice_questions[payload.question_index],
        'level': level, 'hint': generated['hint'] if generated else hints[level - 1], 'language': payload.language,
        'provider': 'template', 'model': None, 'policy': 'guided_practice',
        'generation_note': 'Misconception-specific deterministic scaffolding; no live inference.',
        'response': payload.response, 'next_action': 'TRY_PRACTICE' if level == 4 else 'RESPOND_THEN_HINT'}
    if generated:
        result.update(generated)
        result['next_action'] = 'TRY_PRACTICE' if generated['feedback'] == 'correct' else 'REQUEST_TEACHER_REVIEW' if level == 4 else 'RESPOND_THEN_HINT'
    record_evidence(db, assignment.student, assignment.intervention.subject, assignment.intervention.topic,
        'hint', key, result)
    # Both an idempotent user request and a unique consumed level are protected.
    receipt(db, key, data, result)
    receipt(db, f'hint-step:{assignment.id}:{payload.question_index}:{level}', data, result)
    db.commit()
    return result
