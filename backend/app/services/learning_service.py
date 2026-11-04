"""Replayable evidence and bounded deterministic educational decisions."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.learning import LearningDecision, LearningEvent, LearningSession, LearnerState
from app.subject_taxonomy import is_follow_up_code

POLICY_VERSION = 'evidence-v1'
TRANSITIONS = {
 'CREATED': {'AWAITING_ASSESSMENT', 'DIAGNOSIS_PENDING', 'DIAGNOSIS_READY'},
 'AWAITING_ASSESSMENT': {'DIAGNOSIS_PENDING', 'DIAGNOSIS_READY'},
 'DIAGNOSIS_PENDING': {'DIAGNOSIS_READY', 'NEEDS_REVIEW'},
 'DIAGNOSIS_READY': {'AWAITING_TEACHER_APPROVAL', 'NEEDS_REVIEW', 'DIAGNOSIS_PENDING'},
 'AWAITING_TEACHER_APPROVAL': {'INTERVENTION_APPROVED', 'NEEDS_REVIEW', 'DIAGNOSIS_PENDING'},
 'INTERVENTION_APPROVED': {'TUTORING_ACTIVE', 'REASSESSMENT_READY', 'DIAGNOSIS_PENDING'},
 'TUTORING_ACTIVE': {'REASSESSMENT_READY', 'NEEDS_REVIEW', 'DIAGNOSIS_PENDING'},
 'REASSESSMENT_READY': {'REASSESSMENT_SUBMITTED', 'DIAGNOSIS_PENDING'},
 'REASSESSMENT_SUBMITTED': {'PROGRESS_EVALUATED'},
 'PROGRESS_EVALUATED': {'COMPLETED', 'NEEDS_REVIEW'},
 'COMPLETED': {'DIAGNOSIS_PENDING', 'AWAITING_TEACHER_APPROVAL'},
 'NEEDS_REVIEW': {'DIAGNOSIS_PENDING', 'DIAGNOSIS_READY', 'AWAITING_TEACHER_APPROVAL'},
}


def topic_session(db, student_id, subject, topic):
    item = db.scalar(select(LearningSession).where(LearningSession.student_id == student_id,
        LearningSession.subject == subject, LearningSession.topic == topic))
    if item is None:
        item = LearningSession(student_id=student_id, subject=subject, topic=topic)
        db.add(item)
        db.flush()
    return item


def transition(db, session_id, target, actor, source_key, *, approved=False):
    item = db.get(LearningSession, uuid.UUID(str(session_id)))
    if item is None:
        raise LookupError('Learning session not found')
    if target == 'INTERVENTION_APPROVED' and not approved:
        raise PermissionError('TEACHER_APPROVAL_REQUIRED')
    key = f'transition:{item.id}:{source_key}:{target}'
    if db.scalar(select(LearningEvent.id).where(LearningEvent.source_key == key)) or target == item.state:
        return item
    if target not in TRANSITIONS.get(item.state, set()):
        raise ValueError(f'INVALID_TRANSITION: {item.state} -> {target}')
    db.add(LearningEvent(student_id=item.student_id, subject=item.subject, topic=item.topic,
        kind='transition', source_key=key, data={'prior': item.state, 'next': target, 'actor': actor}))
    item.state = target
    db.flush()
    return item


def project(events):
    observations, hints = {}, 0
    for event in events:
        if event.kind in {'diagnosis', 'reassessment', 'correction'}:
            observations[event.data.get('observation_id', event.source_key)] = {**event.data, 'event_id': str(event.id)}
        if event.kind == 'hint':
            hints += 1
    known = [x for x in observations.values() if isinstance(x.get('correct'), bool) and not x.get('uncertain')]
    recent = known[-10:]
    score = round(100 * sum(x['correct'] for x in recent) / len(recent)) if recent else None
    attempts = {x.get('attempt', x['event_id']) for x in known}
    gaps = {x['code'] for x in observations.values() if x.get('code') and x['code'] not in {'CORRECT', 'FOLLOW_UP'} and not is_follow_up_code(x['code']) and not x.get('uncertain')}
    for code in list(gaps):
        checks = [x for x in observations.values() if x.get('target_code') == code]
        if len(checks) >= 3 and all(x.get('correct') is True for x in checks[-3:]):
            gaps.remove(code)
    secure = len(recent) >= 3 and len(attempts) >= 2 and score >= 80 and not gaps
    return {'mastery_score': score,
        'mastery_category': 'secure' if secure else 'developing' if recent and score >= 50 else 'needs_support' if recent else 'insufficient_evidence',
        'score_note': 'Uncalibrated heuristic from up to 10 independent scored responses; not a probability.',
        'independent_evidence_count': len(known), 'attempt_count': len(attempts),
        'hint_count': hints, 'active_misconceptions': sorted(gaps),
        'difficulty': 'challenging' if secure else 'foundation' if len(recent) >= 3 and score < 40 else 'standard',
        'policy_version': POLICY_VERSION}


def choose_action(state, kind, data):
    if kind == 'hint':
        return 'OFFER_HINT', 'Guided practice hint requested; independent mastery is unchanged.'
    if kind in {'assessment', 'diagnosis_failure'}:
        return 'REQUEST_TEACHER_REVIEW', 'Response saved; validated diagnosis pending.'
    if data.get('uncertain') or is_follow_up_code(data.get('code', '')) or data.get('code') == 'FOLLOW_UP':
        return 'ASK_DIAGNOSTIC_FOLLOWUP', 'Insufficient reasoning evidence; clarify before assigning support.'
    if state['active_misconceptions']:
        return 'ASSIGN_PRACTICE_RECOMMENDATION', 'Evidence identifies ' + ', '.join(state['active_misconceptions']) + '; teacher review required for assignment.'
    if kind == 'practice':
        return 'SCHEDULE_REASSESSMENT_RECOMMENDATION', 'Assisted practice cannot establish mastery; complete practice then check independently.'
    if state['mastery_category'] == 'secure':
        return 'ADJUST_DIFFICULTY', 'Three scored responses across two attempts meet the heuristic; recommend a challenge.'
    return 'REQUEST_TEACHER_REVIEW', 'Limited or mixed evidence; maintain the learning level and request review.'


def record_evidence(db, student, subject, topic, kind, source_key, data):
    old = db.scalar(select(LearningEvent).where(LearningEvent.source_key == source_key))
    if old:
        comparable = {k: v for k, v in old.data.items() if k != 'request_id'}
        if (old.student_id, old.subject, old.topic, old.kind, comparable) != (student.id, subject, topic, kind, data):
            raise ValueError('IDEMPOTENCY_CONFLICT: event key already represents another response')
        return old
    correlation = {'request_id': db.info['request_id']} if db.info.get('request_id') else {}
    item = LearningEvent(student_id=student.id, subject=subject, topic=topic, kind=kind,
        source_key=source_key, data={**data, **correlation}, created_at=datetime.now(timezone.utc))
    db.add(item)
    db.flush()
    session = topic_session(db, student.id, subject, topic)
    events = list(db.scalars(select(LearningEvent).where(LearningEvent.student_id == student.id,
        LearningEvent.subject == subject, LearningEvent.topic == topic,
        LearningEvent.kind != 'transition').order_by(LearningEvent.created_at, LearningEvent.id)))
    projection = project(events)
    state = db.scalar(select(LearnerState).where(LearnerState.student_id == student.id,
        LearnerState.subject == subject, LearnerState.topic == topic))
    if state is None:
        state = LearnerState(student_id=student.id, subject=subject, topic=topic)
        db.add(state)
    state.projection = projection
    action, reason = choose_action(projection, kind, data)
    db.add(LearningDecision(event_id=item.id, action=action, reason=reason,
        requires_teacher_approval=action in {'ASSIGN_PRACTICE_RECOMMENDATION', 'RECOMMEND_LESSON', 'SCHEDULE_REASSESSMENT_RECOMMENDATION'}))
    def move(target, **kw):
        transition(db, session.id, target, 'policy', source_key, **kw)
    if kind == 'assessment':
        move('DIAGNOSIS_PENDING')
    elif kind == 'diagnosis_failure' and session.state == 'DIAGNOSIS_PENDING':
        move('NEEDS_REVIEW')
    elif kind in {'diagnosis', 'correction'}:
        if session.state in {'CREATED', 'AWAITING_ASSESSMENT', 'DIAGNOSIS_PENDING', 'NEEDS_REVIEW'}:
            move('DIAGNOSIS_READY')
        if session.state == 'DIAGNOSIS_READY':
            move('AWAITING_TEACHER_APPROVAL')
    elif kind == 'approved_assignment':
        if session.state in {'CREATED', 'NEEDS_REVIEW'}:
            move('DIAGNOSIS_READY')
        if session.state in {'DIAGNOSIS_READY', 'COMPLETED'}:
            move('AWAITING_TEACHER_APPROVAL')
        transition(db, session.id, 'INTERVENTION_APPROVED', data['teacher_id'], source_key, approved=True)
    elif kind in {'hint', 'practice'} and session.state == 'INTERVENTION_APPROVED':
        move('TUTORING_ACTIVE')
    elif kind == 'activity_completed' and session.state in {'INTERVENTION_APPROVED', 'TUTORING_ACTIVE'}:
        move('REASSESSMENT_READY')
    elif kind == 'reassessment' and session.state == 'REASSESSMENT_READY':
        move('REASSESSMENT_SUBMITTED')
    db.flush()
    return item


def finish_reassessment(db, student_id, subject, topic, source_key):
    session = topic_session(db, student_id, subject, topic)
    if session.state == 'REASSESSMENT_SUBMITTED':
        transition(db, session.id, 'PROGRESS_EVALUATED', 'policy', source_key)
        transition(db, session.id, 'COMPLETED', 'policy', source_key)


def learner_view(db, student_id):
    result = []
    for state in db.scalars(select(LearnerState).where(LearnerState.student_id == student_id).order_by(LearnerState.subject, LearnerState.topic)):
        events = list(db.scalars(select(LearningEvent).where(LearningEvent.student_id == student_id,
            LearningEvent.subject == state.subject, LearningEvent.topic == state.topic).order_by(LearningEvent.created_at, LearningEvent.id)))
        decision = next((d for e in reversed(events) if (d := db.scalar(select(LearningDecision).where(LearningDecision.event_id == e.id)))), None)
        session = topic_session(db, student_id, state.subject, state.topic)
        result.append({'student_id': str(student_id), 'subject': state.subject, 'topic': state.topic,
            **state.projection, 'version': state.version, 'session_id': str(session.id), 'session_state': session.state,
            'decision': {'id': str(decision.id), 'action': decision.action, 'reason': decision.reason,
                'evidence_ids': [str(decision.event_id)], 'requires_teacher_approval': decision.requires_teacher_approval,
                'source': decision.source, 'status': decision.status, 'policy_version': decision.policy_version} if decision else None,
            'events': [{'id': str(e.id), 'kind': e.kind, 'data': e.data, 'created_at': e.created_at.isoformat()} for e in events]})
    return result
