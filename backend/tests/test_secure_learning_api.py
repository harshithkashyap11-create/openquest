"""Credential-backed sessions reject forged headers and cross-class requests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import get_db
from app.core.config import get_settings
from app.models import Teacher, Class, Student

@pytest.fixture
def api(db_session, monkeypatch):
    teacher = Teacher(name='Synthetic teacher', email='secure@test.invalid')
    other = Teacher(name='Other teacher', email='other@test.invalid')
    classroom = Class(teacher=teacher, class_name='Secure fractions')
    other_class = Class(teacher=other, class_name='Other class')
    student = Student(classroom=classroom, student_code='SEC001')
    db_session.add_all([student, other_class])
    db_session.commit()
    monkeypatch.setattr(get_settings(), 'auth_mode', 'required', raising=False)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client, db_session, classroom, other_class, student
    app.dependency_overrides.clear()


def test_unauthenticated_teacher_mutation_rejected(api):
    client, _, classroom, _, student = api
    response = client.post(f'/api/classes/{classroom.id}/groups/generate',
        headers={'X-Demo-Role': 'teacher', 'X-Class-ID': str(classroom.id), 'X-Student-ID': str(student.id)})
    assert response.status_code == 401


def test_login_session_and_class_isolation(api):
    client, db, classroom, other_class, student = api
    assert client.get('/api/auth/config').status_code == 200
    from app.services.auth_service import provision_account
    provision_account(db, 'teacher', 'local-test-password-123', teacher_id=classroom.teacher_id)
    provision_account(db, 'student', 'local-test-password-456', student_id=student.id)
    db.commit()
    result = client.post('/api/auth/login', json={'username': 'teacher', 'password': 'local-test-password-123'})
    assert result.status_code == 200
    csrf = result.json()['csrf_token']
    assert 'HttpOnly' in result.headers['set-cookie']
    assert client.get(f'/api/classes/{classroom.id}/assessment-summary').status_code == 200
    assert client.get(f'/api/classes/{other_class.id}/assessment-summary').status_code == 403
    assert client.post(f'/api/classes/{classroom.id}/groups/generate').status_code == 403
    assert client.post('/api/auth/logout', headers={'X-CSRF-Token': csrf}).status_code == 200
    assert client.get(f'/api/classes/{classroom.id}/assessment-summary').status_code == 401
    result = client.post('/api/auth/login', json={'username': 'student', 'password': 'local-test-password-456'})
    csrf = result.json()['csrf_token']
    headers = {'X-CSRF-Token': csrf, 'X-Demo-Role': 'teacher', 'X-Class-ID': str(classroom.id)}
    assert client.post(f'/api/classes/{classroom.id}/groups/generate', headers=headers).status_code == 403
    assert client.get(f'/api/students/{student.id}/learning-state', headers=headers).status_code == 200
    assert client.get(f'/api/classes/{classroom.id}/diagnoses', headers=headers).status_code == 403
    assert client.get(f'/api/students/{student.id}/progress', headers={'X-Student-ID': str(student.id)}).status_code == 200
