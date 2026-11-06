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
    from app.services.rate_limit_service import _buckets
    _buckets.clear()
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
    assert client.get(f'/api/students/{student.id}/progress').status_code == 200


def test_inclusive_support_catalog_is_teacher_and_class_scoped(api):
    client, db, classroom, other_class, student = api
    from app.services.auth_service import provision_account
    provision_account(db, 'inclusive-teacher', 'local-test-password-123', teacher_id=classroom.teacher_id)
    provision_account(db, 'inclusive-student', 'local-test-password-456', student_id=student.id)
    db.commit()
    client.post('/api/auth/login', json={'username': 'inclusive-teacher', 'password': 'local-test-password-123'})
    response = client.get(f'/api/classes/{classroom.id}/inclusive/supports')
    assert response.status_code == 200
    assert any(item['id'] == 'READ-002' for item in response.json()['supports'])
    assert client.get(f'/api/classes/{other_class.id}/inclusive/supports').status_code == 403
    csrf = client.get('/api/auth/me').json()['csrf_token']
    client.post('/api/auth/logout', headers={'X-CSRF-Token': csrf})
    client.post('/api/auth/login', json={'username': 'inclusive-student', 'password': 'local-test-password-456'})
    assert client.get(f'/api/classes/{classroom.id}/inclusive/supports').status_code == 403


def test_inclusive_source_is_persisted_and_class_scoped(api):
    import base64
    client, db, classroom, other_class, _ = api
    from app.services.auth_service import provision_account
    provision_account(db, 'source-teacher', 'local-test-password-123', teacher_id=classroom.teacher_id)
    db.commit()
    login = client.post('/api/auth/login', json={'username': 'source-teacher', 'password': 'local-test-password-123'})
    headers = {'X-CSRF-Token': login.json()['csrf_token']}
    data = {'filename': 'lesson.txt', 'content_base64': base64.b64encode(b'Plants need light and water to make their food.').decode()}
    result = client.post(f'/api/classes/{classroom.id}/inclusive/sources', json=data, headers=headers)
    assert result.status_code == 201, result.text
    assert result.json()['source']['blocks'][0]['text'] == 'Plants need light and water to make their food.'
    listed = client.get(f'/api/classes/{classroom.id}/inclusive/sources')
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert client.get(f'/api/classes/{other_class.id}/inclusive/sources').status_code == 403
    assert client.post(f'/api/classes/{classroom.id}/inclusive/sources', json={'filename':'bad.exe','content_base64':data['content_base64']}, headers=headers).status_code == 415


def test_inclusive_lifecycle_requires_current_review_and_hides_answers(api, monkeypatch):
    import base64
    from app.services.auth_service import provision_account
    from app.services import inclusive_learning
    client, db, classroom, _, student = api
    provision_account(db, 'life-teacher', 'local-test-password-123', teacher_id=classroom.teacher_id)
    provision_account(db, 'life-student', 'local-test-password-456', student_id=student.id)
    db.commit()
    login = client.post('/api/auth/login', json={'username': 'life-teacher', 'password': 'local-test-password-123'})
    headers = {'X-CSRF-Token': login.json()['csrf_token']}
    data = {'filename': 'lesson.txt', 'content_base64': base64.b64encode(b'Plants need light and water to make their food.').decode()}
    source = client.post(f'/api/classes/{classroom.id}/inclusive/sources', json=data, headers=headers).json()
    def fake_generate(source_data, profile):
        return {'analysis': {}, 'draft': {'title': 'Plants', 'text': 'Plants need light.', 'objectives': ['Describe plant needs'], 'questions': [{'prompt': 'What do plants need?', 'answer': 'light', 'hints': ['Look at the lesson']}]}, 'findings': [{'status': 'needs_review', 'message': 'Teacher review required', 'source_ref': 'source', 'evidence': ''}]}
    monkeypatch.setattr(inclusive_learning, 'generate_adaptation', fake_generate, raising=False)
    base = f'/api/classes/{classroom.id}/inclusive'
    made = client.post(f'{base}/adaptations', json={'source_id': source['id'], 'support_ids': ['READ-002']}, headers=headers)
    assert made.status_code == 201, made.text
    item = made.json(); aid = item['id']
    assert client.post(f'{base}/adaptations/{aid}/assign', json={'student_ids': [str(student.id)]}, headers=headers).status_code == 409
    approved = client.post(f'{base}/adaptations/{aid}/approve', json={'version': 1, 'review_note': 'Reviewed lesson, findings and answer keys.'}, headers=headers)
    assert approved.status_code == 200, approved.text
    assert client.post(f'{base}/adaptations/{aid}/assign', json={'student_ids': [str(student.id)]}, headers=headers).status_code == 200
    history = client.get(f'{base}/adaptations/{aid}/history')
    assert [entry['action'] for entry in history.json()] == ['generated', 'approved']
    csrf = headers['X-CSRF-Token']; client.post('/api/auth/logout', headers={'X-CSRF-Token': csrf})
    login = client.post('/api/auth/login', json={'username': 'life-student', 'password': 'local-test-password-456'})
    lessons = client.get(f'/api/students/{student.id}/inclusive/lessons')
    assert lessons.status_code == 200, lessons.text
    payload = lessons.json()[0]
    assert 'answer' not in str(payload).lower() and 'support' not in str(payload).lower()
    attempt = client.post(f"/api/students/{student.id}/inclusive/lessons/{payload['id']}/practice", json={'answers': ['light']}, headers={'X-CSRF-Token': login.json()['csrf_token']})
    assert attempt.status_code == 200 and attempt.json()['results'][0]['correct'] is True
    saved = client.get(f'/api/students/{student.id}/inclusive/lessons').json()[0]
    assert saved['progress']['results'][0]['correct'] is True


def test_inclusive_edit_invalidates_review_and_requires_current_version(api, monkeypatch):
    import base64
    from app.services.auth_service import provision_account
    from app.services import inclusive_learning
    client, db, classroom, _, _ = api
    provision_account(db, 'edit-teacher', 'local-test-password-123', teacher_id=classroom.teacher_id); db.commit()
    login = client.post('/api/auth/login', json={'username': 'edit-teacher', 'password': 'local-test-password-123'})
    headers = {'X-CSRF-Token': login.json()['csrf_token']}
    base = f'/api/classes/{classroom.id}/inclusive'
    source = client.post(f'{base}/sources', json={'filename':'lesson.txt', 'content_base64':base64.b64encode(b'Plants need light and water to make their food.').decode()}, headers=headers).json()
    monkeypatch.setattr(inclusive_learning, 'generate_adaptation', lambda *_: {'analysis': {}, 'bridge_draft': {'blocks': [{'block_id':'b1','content':'Plants use light.'}]}, 'draft': {'title':'Plants','objectives':['Plant needs'],'text':'Plants use light.','questions':[]},'findings':[{'status':'NEEDS_REVIEW'}]}, raising=False)
    item = client.post(f'{base}/adaptations', json={'source_id':source['id'],'support_ids':['READ-002']}, headers=headers).json()
    endpoint = f"{base}/adaptations/{item['id']}"
    assert client.post(endpoint+'/approve', json={'version':1,'review_note':'Reviewed all the material.'}, headers=headers).status_code == 200
    edit = client.patch(endpoint, json={'version':1,'blocks':[{'block_id':'b1','content':'Plants use sunlight.'}], 'questions':[]}, headers=headers)
    assert edit.status_code == 200, edit.text
    assert edit.json()['version'] == 2 and edit.json()['approved_version'] is None and not edit.json()['findings']
    assert client.post(endpoint+'/approve', json={'version':2,'review_note':'Reviewed all the material.'}, headers=headers).status_code == 409
    assert client.patch(endpoint, json={'version':1,'blocks':[{'block_id':'b1','content':'Stale change.'}], 'questions':[]}, headers=headers).status_code == 409
    monkeypatch.setattr(inclusive_learning, 'reverify_adaptation', lambda *_: [{'status':'NEEDS_REVIEW','explanation':'Teacher review required'}])
    checked = client.post(endpoint+'/verify', json={'version':2, 'review_note':'Request verification'}, headers=headers)
    assert checked.status_code == 200 and checked.json()['findings']
    assert client.post(endpoint+'/approve', json={'version':2,'review_note':'Reviewed all the material.'}, headers=headers).status_code == 200


def test_inclusive_can_use_existing_english_lesson(api):
    from app.models.lesson import Lesson, LessonRevision
    from app.services.auth_service import provision_account
    client, db, classroom, _, _ = api
    provision_account(db, 'existing-teacher', 'local-test-password-123', teacher_id=classroom.teacher_id)
    lesson = Lesson(class_id=classroom.id, subject='Math', topic='Fractions', misconception_code='M01', created_by=classroom.teacher_id, generation_context={})
    db.add(lesson); db.flush()
    content = {'title':'Fractions','objectives':['Add fractions'], 'explanation':'Find a common denominator.', 'misconception_correction':'Keep the denominator.', 'worked_example':{'problem':'1/2 + 1/2','steps':['Add the numerators.'],'answer':'1'}, 'practice_questions':[{'prompt':'1/2 + 1/2?', 'answer':'1', 'hints':['Add']}], 'exit_ticket':{'prompt':'1/3 + 1/3?', 'answer':'2/3', 'hints':['Add']}}
    db.add(LessonRevision(lesson_id=lesson.id, revision_no=1, language='en', content=content, provider='template', generation_note='review')); db.commit()
    login=client.post('/api/auth/login',json={'username':'existing-teacher','password':'local-test-password-123'})
    result=client.post(f'/api/classes/{classroom.id}/inclusive/sources/from-lesson',json={'lesson_id':str(lesson.id)},headers={'X-CSRF-Token':login.json()['csrf_token']})
    assert result.status_code == 201, result.text
    assert 'Find a common denominator' in str(result.json()['source'])
    assert 'answer' not in str(result.json()['source']).lower()


def test_inclusive_exports_are_escaped_and_drafts_marked(api, monkeypatch):
    import base64
    from app.services.auth_service import provision_account
    from app.services import inclusive_learning
    client, db, classroom, _, _ = api
    provision_account(db, 'export-teacher', 'local-test-password-123', teacher_id=classroom.teacher_id); db.commit()
    login = client.post('/api/auth/login', json={'username':'export-teacher','password':'local-test-password-123'})
    headers={'X-CSRF-Token':login.json()['csrf_token']}; base=f'/api/classes/{classroom.id}/inclusive'
    source=client.post(base+'/sources',json={'filename':'lesson.txt','content_base64':base64.b64encode(b'Plants need light and water to make their food.').decode()},headers=headers).json()
    monkeypatch.setattr(inclusive_learning,'generate_adaptation',lambda *_:{'analysis':{},'draft':{'title':'<script>x</script>','text':'Plants need light.','objectives':['Plant needs'],'questions':[]},'findings':[{'status':'NEEDS_REVIEW'}]})
    item=client.post(base+'/adaptations',json={'source_id':source['id'],'support_ids':['READ-002']},headers=headers).json()
    result=client.get(f"{base}/adaptations/{item['id']}/export/html")
    assert result.status_code == 200 and 'DRAFT — NOT APPROVED' in result.text
    assert '<script>' not in result.text and '&lt;script&gt;' in result.text
    assert client.get(f"{base}/adaptations/{item['id']}/export/pdf").content.startswith(b'%PDF')
    assert '<speak' in client.get(f"{base}/adaptations/{item['id']}/export/ssml").text
