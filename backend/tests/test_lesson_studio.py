import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models import Teacher, Class, Student

@pytest.fixture
def studio(db_session):
    teacher = Teacher(name='Lesson teacher', email='lessons@test.invalid')
    classroom = Class(teacher=teacher, class_name='Lesson fractions')
    student = Student(student_code='LESSON01', classroom=classroom)
    db_session.add(student)
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client, classroom, student
    app.dependency_overrides.clear()


def test_teacher_reviewed_lesson_versions_and_student_visibility(studio):
    client, classroom, student = studio
    th = {'X-Demo-Role': 'teacher', 'X-Class-ID': str(classroom.id)}
    sh = {'X-Demo-Role': 'student', 'X-Student-ID': str(student.id)}
    created = client.post(f'/api/classes/{classroom.id}/lessons/generate', headers=th,
        json={'misconception_code': 'M01', 'language': 'en', 'request_id': 'lesson-create-1'})
    assert created.status_code == 201, created.text
    lesson = created.json()
    lid, rid = lesson['id'], lesson['revision']['id']
    assert lesson['revision']['provider'] == 'template'
    assert client.get(f'/api/students/{student.id}/lessons', headers=sh).json() == []
    review_url = f'/api/lessons/{lid}/review'
    assert client.post(review_url, headers=sh, json={'revision_id': rid, 'action': 'publish'}).status_code == 403
    assert client.post(review_url, headers=th, json={'revision_id': rid, 'action': 'publish'}).status_code == 409
    assert client.post(review_url, headers=th, json={'revision_id': rid, 'action': 'approve'}).status_code == 422
    approved = client.post(review_url, headers=th, json={'revision_id': rid, 'action': 'approve', 'answer_keys_reviewed': True, 'language_reviewed': True})
    assert approved.status_code == 200, approved.text
    assert client.post(review_url, headers=th, json={'revision_id': rid, 'action': 'publish'}).status_code == 200
    published = client.get(f'/api/students/{student.id}/lessons', headers=sh).json()
    assert len(published) == 1
    assert 'answer' not in published[0]['revision']['content']['practice_questions'][0]
    content = lesson['revision']['content']
    content['explanation'] += ' Teacher addition.'
    updated = client.patch(f'/api/lessons/{lid}', headers=th, json={'revision_id': rid, 'content': content})
    assert updated.status_code == 200, updated.text
    assert updated.json()['revision']['status'] == 'draft'
    assert client.post(review_url, headers=th, json={'revision_id': rid, 'action': 'approve', 'answer_keys_reviewed': True, 'language_reviewed': True}).status_code == 409
    assert client.get(f'/api/students/{student.id}/lessons', headers=sh).json()[0]['revision']['id'] == rid
    assert client.patch(f'/api/lessons/{lid}', headers=th, json={'revision_id': rid, 'content': content}).status_code == 409


def test_lesson_retry_and_unsupported_language_or_code(studio):
    client, classroom, student = studio
    headers = {'X-Demo-Role': 'teacher', 'X-Class-ID': str(classroom.id)}
    url = f'/api/classes/{classroom.id}/lessons/generate'
    payload = {'misconception_code': 'M01', 'language': 'te', 'request_id': 'lesson-create-2'}
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 201
    second = client.post(url, headers=headers, json=payload)
    assert second.json()['id'] == first.json()['id']
    payload['language'] = 'hi'
    assert client.post(url, headers=headers, json=payload).status_code == 409
    payload['request_id'] = 'lesson-create-3'
    payload['misconception_code'] = 'FM01'
    assert client.post(url, headers=headers, json=payload).status_code == 422


def test_generation_context_and_assignment_to_already_approved_work(studio):
    client, classroom, student = studio
    headers = {'X-Demo-Role':'teacher','X-Class-ID':str(classroom.id)}
    response = client.post(f'/api/classes/{classroom.id}/lessons/generate', headers=headers,
        json={'misconception_code':'M01','language':'en','request_id':'context-request-1','duration_minutes':15,'difficulty':'foundation'})
    assert response.status_code == 201, response.text
    lesson = response.json()
    assert lesson['generation_context']['enrolled_students'] == 1
    assert lesson['generation_context']['difficulty'] == 'foundation'
    assert lesson['generation_context']['evidence_ids'] == []
    assert client.post(f'/api/lessons/{lesson["id"]}/assign', headers=headers,
        json={'revision_id':lesson['revision']['id']}).status_code == 409
