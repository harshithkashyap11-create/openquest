import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Class, Student
from app.models.access import AuthAccount, AuthSession
from app.services.auth_service import COOKIE, hash_token, password_hash, session_account

router = APIRouter(prefix='/api/auth', tags=['authentication'])

class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)

@router.get('/config')
def auth_config():
    return {'mode': get_settings().auth_mode, 'demo_identity': get_settings().auth_mode == 'demo'}


def account_view(db, account, csrf):
    student = db.get(Student, account.student_id) if account.student_id else None
    classes = list(db.scalars(select(Class).where(Class.id == student.class_id if student else Class.teacher_id == account.teacher_id).order_by(Class.class_name)))
    return {'role': 'student' if student else 'teacher', 'actorId': str(account.student_id or account.teacher_id),
        'studentId': str(student.id) if student else None, 'studentCode': student.student_code if student else None,
        'csrf_token': csrf, 'authenticated': True,
        'classes': [{'id': str(c.id), 'class_name': c.class_name, 'subject': c.subject, 'topic': c.topic} for c in classes]}

@router.post('/login')
def login(payload: LoginInput, request: Request, response: Response, db=Depends(get_db)):
    from app.services.rate_limit_service import check_rate
    check_rate(('login', request.client.host if request.client else 'unknown'), 10)
    account = db.scalar(select(AuthAccount).where(AuthAccount.username == payload.username))
    stored = account.password_hash if account else password_hash('invalid-credentials', 'constant-time-salt')
    _, salt, _ = stored.split('$')
    valid = hmac.compare_digest(stored, password_hash(payload.password, salt))
    if not account or not valid:
        raise HTTPException(401, 'INVALID_CREDENTIALS')
    # Remove expired tokens without exposing or storing the actual session token.
    db.execute(delete(AuthSession).where(AuthSession.expires_at < datetime.now(timezone.utc)))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=hash_token(token), account_id=account.id, csrf_token=csrf,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=get_settings().session_hours)))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=get_settings().app_env not in {'development', 'test'},
        samesite='strict', max_age=get_settings().session_hours * 3600, path='/')
    return account_view(db, account, csrf)

@router.get('/me')
def auth_me(request: Request, db=Depends(get_db)):
    account, session = session_account(request, db)
    return account_view(db, account, session.csrf_token)

@router.post('/logout')
def logout(request: Request, response: Response, db=Depends(get_db)):
    _, session = session_account(request, db)
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'status': 'signed_out'}
