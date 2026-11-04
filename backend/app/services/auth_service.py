"""Local credentials, opaque HttpOnly sessions, server-side role/class scoping."""
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Class, Student, Teacher, LearningGroup, InterventionAssignment, Reassessment, Quiz, Diagnosis, Submission
from app.models.access import AuthAccount, AuthSession

COOKIE = 'classpulse_session'
STUDENT_ROUTES = {
 'class_assessment', 'submit_assessment', 'student_progress', 'list_student_interventions',
 'get_intervention_assignment', 'submit_intervention_answers', 'complete_intervention',
 'get_or_create_reassessment', 'get_reassessment_result', 'submit_reassessment_answers',
 'student_quizzes', 'student_quiz', 'submit_quiz', 'reflect', 'repair',
 'student_learning_state', 'student_lessons', 'lesson_detail', 'tutor_history', 'request_hint',
 'sync_practice', 'auth_me', 'logout', 'demo_classes',
}


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600_000).hex()
    return f'pbkdf2_sha256${salt}${digest}'


def provision_account(db, username, password, *, teacher_id=None, student_id=None):
    if bool(teacher_id) == bool(student_id) or len(password) < 12:
        raise ValueError('Provide one existing actor and a password of at least 12 characters')
    if (db.get(Teacher, teacher_id) if teacher_id else db.get(Student, student_id)) is None:
        raise ValueError('Actor not found')
    if db.scalar(select(AuthAccount.id).where(AuthAccount.username == username)):
        raise ValueError('Account already exists; credentials were not overwritten')
    account = AuthAccount(username=username, password_hash=password_hash(password), teacher_id=teacher_id, student_id=student_id)
    db.add(account)
    db.flush()
    return account


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def session_account(request, db):
    token = request.cookies.get(COOKIE)
    session = db.get(AuthSession, hash_token(token)) if token else None
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(401, 'AUTHENTICATION_REQUIRED')
    account = db.get(AuthAccount, session.account_id)
    if not account:
        raise HTTPException(401, 'AUTHENTICATION_REQUIRED')
    return account, session


def actor_for(request, db):
    if hasattr(request.state, 'actor'):
        return request.state.actor
    if get_settings().auth_mode == 'required':
        account, _ = session_account(request, db)
        actor = {'role': 'teacher' if account.teacher_id else 'student',
            'id': account.teacher_id or account.student_id, 'authenticated': True}
    else:
        role = request.headers.get('X-Demo-Role', 'student' if request.headers.get('X-Student-ID') else 'teacher')
        actor_id = request.headers.get('X-Student-ID') if role == 'student' else None
        actor = {'role': role, 'id': UUID(actor_id) if actor_id else None, 'authenticated': False}
    request.state.actor = actor
    return actor


def require_teacher(request, db, class_id):
    actor = actor_for(request, db)
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise HTTPException(404, 'Class not found')
    if actor['role'] != 'teacher' or (actor['authenticated'] and actor['id'] != classroom.teacher_id):
        raise HTTPException(403, 'CLASS_ACCESS_DENIED')
    return classroom.teacher_id


def _resource_scope(request, db):
    params = request.path_params
    class_ids, student_ids = [], []
    if params.get('class_id'):
        class_ids.append(UUID(str(params['class_id'])))
    if params.get('student_id'):
        sid = UUID(str(params['student_id']))
        student = db.get(Student, sid)
        if student is None:
            raise HTTPException(404, 'Student not found')
        class_ids.append(student.class_id)
        student_ids.append(sid)
    for param, model in [('group_id', LearningGroup), ('assignment_id', InterventionAssignment), ('reassessment_id', Reassessment), ('quiz_id', Quiz), ('diagnosis_id', Diagnosis)]:
        if param not in params:
            continue
        item = db.get(model, UUID(str(params[param])))
        if item is None:
            raise HTTPException(404, 'Resource not found')
        if model == Diagnosis:
            item = db.get(Submission, item.submission_id)
        if model == Reassessment:
            item = db.get(InterventionAssignment, item.assignment_id)
        if hasattr(item, 'student_id'):
            student = db.get(Student, item.student_id)
            student_ids.append(student.id)
            class_ids.append(student.class_id)
        else:
            class_ids.append(item.class_id)
    if params.get('lesson_id'):
        from app.models.lesson import Lesson
        lesson = db.get(Lesson, UUID(str(params['lesson_id'])))
        if lesson is None:
            raise HTTPException(404, 'Lesson not found')
        class_ids.append(lesson.class_id)
    return class_ids, student_ids


async def authorize_request(request: Request, db=Depends(get_db)):
    from starlette.concurrency import run_in_threadpool
    body = None
    if request.url.path.endswith('/chat') and '/copilot/' in request.url.path:
        try:
            body = await request.json()
        except ValueError as error:
            raise HTTPException(422, 'INVALID_JSON') from error
    return await run_in_threadpool(_authorize_sync, request, db, body)


def _authorize_sync(request, db, body):
    request.state.db = db
    if hasattr(db, 'info'):
        db.info['request_id'] = getattr(request.state, 'request_id', None)
    path = request.url.path
    if not path.startswith('/api/') or path in {'/api/auth/config', '/api/auth/login'}:
        return
    settings = get_settings()
    # Legacy demo calls remain compatible; demo mode is prohibited in shared
    # deployment settings and visibly labeled as self-asserted identity.
    if settings.auth_mode == 'demo' and not request.headers.get('X-Demo-Role'):
        return
    actor = actor_for(request, db)
    if settings.auth_mode == 'required' and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        _, session = session_account(request, db)
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), session.csrf_token):
            raise HTTPException(403, 'CSRF_CHECK_FAILED')
    name = request.scope['route'].name
    if path.startswith('/api/auth/'):
        return
    if settings.auth_mode == 'required' and '/demo/' in path and name != 'demo_classes':
        raise HTTPException(403, 'DEMO_IDENTITY_DISABLED')
    try:
        classes, students = _resource_scope(request, db)
    except ValueError as error:
        raise HTTPException(422, 'INVALID_RESOURCE_IDENTIFIER') from error
    if settings.auth_mode == 'required' and request.method == 'POST' and any(part in path for part in ('/diagnose', '/generate', '/reflect', '/chat')):
        from app.services.rate_limit_service import check_rate
        check_rate(('inference', str(actor['id'])), 10)
    if path.endswith('/chat') and '/copilot/' in path:
        if isinstance(body, dict) and body.get('class_id'):
            try:
                classes.append(UUID(str(body['class_id'])))
            except ValueError as error:
                raise HTTPException(422, 'INVALID_RESOURCE_IDENTIFIER') from error
    if actor['role'] == 'student':
        if name not in STUDENT_ROUTES:
            raise HTTPException(403, 'TEACHER_ROLE_REQUIRED')
        own = db.get(Student, actor['id'])
        if own is None or any(c != own.class_id for c in classes) or any(s != own.id for s in students):
            raise HTTPException(403, 'STUDENT_ACCESS_DENIED')
        asserted = request.headers.get('X-Student-ID')
        if asserted and asserted != str(own.id):
            raise HTTPException(403, 'STUDENT_ACCESS_DENIED')
        # Existing student routes accept an identity header. Supply the verified
        # identity internally when a cookie-authenticated client omits it.
        headers = [(k, v) for k, v in request.scope['headers'] if k.lower() != b'x-student-id']
        request.scope['headers'] = headers + [(b'x-student-id', str(own.id).encode())]
        if hasattr(request, '_headers'):
            del request._headers
    elif actor['role'] == 'teacher':
        if name in STUDENT_ROUTES and request.method not in {'GET', 'HEAD'}:
            raise HTTPException(403, 'STUDENT_ROLE_REQUIRED')
        for class_id in classes:
            require_teacher(request, db, class_id)
        if name in {'preview_import'}:
            selected = request.headers.get('X-Class-ID')
            if not selected:
                raise HTTPException(403, 'CLASS_CONTEXT_REQUIRED')
            require_teacher(request, db, UUID(selected))
    else:
        raise HTTPException(403, 'ROLE_NOT_ALLOWED')
