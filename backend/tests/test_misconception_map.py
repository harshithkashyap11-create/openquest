"""Map counts, evidence and isolation use persisted records, never provider output."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models import Class, Diagnosis, GroupMember, LearningGroup, Student, Submission, Teacher
from app.services.auth_service import provision_account
from test_grouping_service import _add_diagnosis


@pytest.fixture
def map_api(db_session):
    classroom = Class(class_name='Synthetic map test', teacher=Teacher(name='Test', email='map@test.invalid'))
    foreign = Class(class_name='Foreign', teacher=Teacher(name='Other', email='foreign-map@test.invalid'))
    db_session.add_all([classroom, foreign]); db_session.flush()
    first = _add_diagnosis(db_session, classroom, 'M01', .9, 'TEST-01')
    _add_diagnosis(db_session, classroom, 'M01', .6, 'TEST-02')
    _add_diagnosis(db_session, classroom, 'M06', .9, 'TEST-03')
    _add_diagnosis(db_session, foreign, 'M02', .9, 'FOREIGN')
    diagnosis = db_session.scalar(select(Diagnosis).where(Diagnosis.submission.has(student_id=first.id)))
    diagnosis.evidence = '2/5'
    diagnosis.misunderstanding_explanation = 'Possible addition of unlike parts.'
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client, db_session, classroom, foreign, first, diagnosis
    finally:
        app.dependency_overrides.clear()


def test_map_counts_reconcile_and_correction_keeps_original_evidence(map_api):
    client, db, c, _, student, diagnosis = map_api
    url = f'/api/classes/{c.id}/misconception-map'
    response = client.get(url)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['total_responses'] == 3
    assert data['attention'] == {'pending_diagnoses': 0, 'pending_reviews': 3, 'uncertain': 2, 'proposed_groups': 0, 'ready_for_reassessment': 0}
    assert [(x['code'], x['response_count'], x['student_count']) for x in data['concepts']] == [('M01', 2, 2), ('M06', 1, 1)]
    assert '2/5' not in response.text  # Full response bodies belong only in detail.
    detail = client.get(url + '/evidence', params={'code': 'M01', 'limit': 1}).json()
    assert detail['total'] == 2 and len(detail['items']) == 1
    item = client.get(url + '/evidence', params={'code': 'M01', 'student_id': str(student.id)}).json()['items'][0]
    assert item['answer'] == '2/5' and item['question_text'] == 'Question for TEST-01'
    assert item['ai_explanation'] == 'Possible addition of unlike parts.'
    assert item['review'] is None
    saved = client.post(f'/api/diagnoses/{diagnosis.id}/corrections', json={'code': 'CORRECT', 'reason': 'Synthetic test review', 'expected_version': 0, 'request_id': 'map-correction-01'})
    assert saved.status_code == 200
    updated = client.get(url).json()
    assert updated['attention']['pending_reviews'] == 2
    assert updated['concepts'][0]['code'] == 'CORRECT'
    item = client.get(url + '/evidence', params={'code': 'CORRECT'}).json()['items'][0]
    assert item['original_code'] == 'M01' and item['review']['code'] == 'CORRECT'
    assert item['review']['teacher_id'] == str(c.teacher_id)
    assert item['answer'] == '2/5'


def test_map_uses_latest_attempt_and_reports_pending_without_old_suggestion(map_api):
    client, db, c, _, student, diagnosis = map_api
    db.add(Submission(student_id=student.id, question_id=diagnosis.submission.question_id, attempt_no=2, answer='5/6'))
    db.commit()
    data = client.get(f'/api/classes/{c.id}/misconception-map').json()
    assert data['total_responses'] == 3
    assert data['attention']['pending_diagnoses'] == 1
    assert sum(x['response_count'] for x in data['concepts']) == 2


def test_map_empty_pagination_and_student_role(map_api):
    client, db, c, _, student, _ = map_api
    empty = Class(class_name='Empty', teacher_id=c.teacher_id)
    db.add(empty); db.commit()
    assert client.get(f'/api/classes/{empty.id}/misconception-map').json()['concepts'] == []
    url = f'/api/classes/{c.id}/misconception-map'
    assert client.get(url + '/evidence?limit=101').status_code == 422
    assert client.get(url + '/evidence?offset=-1').status_code == 422
    assert client.get(url + '/evidence?code=INVENTED').status_code == 422
    assert client.get(url, headers={'X-Demo-Role': 'student', 'X-Student-ID': str(student.id)}).status_code == 403
    assert client.get(f'/api/classes/{uuid4()}/misconception-map').status_code == 404


def test_required_auth_cannot_read_foreign_map_or_journey(map_api, monkeypatch):
    client, db, c, foreign, student, _ = map_api
    provision_account(db, 'map-teacher', 'test-map-password-only', teacher_id=c.teacher_id); db.commit()
    monkeypatch.setattr(get_settings(), 'auth_mode', 'required')
    assert client.get(f'/api/classes/{c.id}/misconception-map').status_code == 401
    assert client.post('/api/auth/login', json={'username': 'map-teacher', 'password': 'test-map-password-only'}).status_code == 200
    assert client.get(f'/api/classes/{c.id}/misconception-map').status_code == 200
    denied = client.get(f'/api/classes/{foreign.id}/misconception-map')
    assert denied.status_code in {403, 404} and 'FOREIGN' not in denied.text


def test_journey_has_source_responses_and_no_invented_support(map_api):
    client, _, _, _, student, diagnosis = map_api
    data = client.get(f'/api/students/{student.id}/journey', headers={'X-Student-ID': str(student.id)}).json()
    assert data['events'][0]['kind'] == 'response'
    assert data['events'][0]['source_id'] == str(diagnosis.submission_id)
    assert data['events'][0]['answer'] == '2/5'
    assert not any(e['kind'] == 'support' for e in data['events'])


def test_group_approval_rejects_persisted_foreign_member(map_api):
    client, db, c, foreign, student, _ = map_api
    other = db.scalar(select(Student).where(Student.class_id == foreign.id))
    group = LearningGroup(class_id=c.id, topic=c.topic, misconception_code='M01', name='Test unsafe proposal', teacher_approved=False)
    db.add(group); db.flush()
    db.add_all([GroupMember(group_id=group.id, student_id=student.id), GroupMember(group_id=group.id, student_id=other.id)])
    db.commit()
    response = client.patch(f'/api/groups/{group.id}/review', json={'status': 'approved'})
    assert response.status_code == 409
    db.refresh(group)
    assert group.review_status == 'proposed' and not group.teacher_approved


def test_system_status_reports_configuration_without_a_provider_request(map_api):
    client, _, _, _, _, _ = map_api
    response = client.get('/api/system-status')
    assert response.status_code == 200
    assert response.json()['database'] == 'available'
    assert response.json()['provider_reachability'] == 'not_tested'
    assert set(response.json()) == {'app', 'database', 'ai_provider', 'provider_reachability', 'checked_at'}


def test_assignment_rechecks_foreign_members_even_for_legacy_approved_group(map_api):
    client, db, c, foreign, student, _ = map_api
    other = db.scalar(select(Student).where(Student.class_id == foreign.id))
    group = LearningGroup(class_id=c.id, topic=c.topic, misconception_code='M01', name='Unsafe legacy group',
        teacher_approved=True, review_status='approved')
    db.add(group); db.flush()
    db.add_all([GroupMember(group_id=group.id, student_id=student.id), GroupMember(group_id=group.id, student_id=other.id)])
    db.commit()
    response = client.post(f'/api/groups/{group.id}/interventions/generate')
    assert response.status_code == 409
    from app.models import InterventionAssignment
    assert db.scalar(select(InterventionAssignment.id).where(InterventionAssignment.student_id == other.id)) is None


def test_attention_readiness_and_journey_follow_saved_assignment_and_result(map_api):
    client, db, c, _, student, _ = map_api
    for diagnosis in db.scalars(select(Diagnosis).where(Diagnosis.submission.has(Submission.student.has(class_id=c.id)))):
        if diagnosis.misconception_code == 'M01':
            diagnosis.confidence = .9
    db.commit()
    group = client.post(f'/api/classes/{c.id}/groups/generate').json()['groups'][0]
    assert client.patch(f'/api/groups/{group["id"]}/review', json={'status': 'approved', 'expected_revision': group['revision']}).status_code == 200
    generated = client.post(f'/api/groups/{group["id"]}/interventions/generate').json()
    assignment = next(a for a in generated['assignments'] if a['student_id'] == str(student.id))
    assignment_id = assignment['id']
    headers = {'X-Student-ID': str(student.id), 'X-Demo-Role': 'student'}
    answers = [{'question_index': index, 'answer': answer} for index, answer in enumerate(generated['intervention']['expected_answers'])]
    assert client.post(f'/api/intervention-assignments/{assignment_id}/submit', headers=headers, json={'answers': answers}).status_code == 200
    assert client.get(f'/api/classes/{c.id}/misconception-map').json()['attention']['ready_for_reassessment'] == 0
    completed = client.post(f'/api/intervention-assignments/{assignment_id}/complete', headers=headers, json={})
    assert completed.status_code == 200, completed.text
    assert client.get(f'/api/classes/{c.id}/misconception-map').json()['attention']['ready_for_reassessment'] == 1
    reassessment_id = completed.json()['reassessment']['id']
    result = client.post(f'/api/reassessments/{reassessment_id}/submit', headers=headers, json={'answers': [
        {'question_id': q['id'], 'answer': answer}
        for q, answer in zip(completed.json()['reassessment']['questions'], ['11/12', '7/10', '13/24'])]})
    assert result.status_code == 200, result.text
    assert client.get(f'/api/classes/{c.id}/misconception-map').json()['attention']['ready_for_reassessment'] == 0
    events = client.get(f'/api/students/{student.id}/journey', headers=headers).json()['events']
    assert [e['kind'] for e in events].count('response') == 1
    support = next(e for e in events if e['kind'] == 'support')
    followup = next(e for e in events if e['kind'] == 'reassessment')
    assert support['source_id'] == assignment_id == followup['assignment_id']
    assert followup['source_id'] == reassessment_id and followup['correct'] == 3 and followup['total'] == 3
    from datetime import datetime
    timestamps = [datetime.fromisoformat(e['at']) for e in events]
    assert timestamps == sorted(timestamps)


def test_latest_suggestion_deduplicates_and_threshold_is_inclusive(map_api):
    from datetime import datetime, timezone, timedelta
    client, db, c, _, _, original = map_api
    db.add(Diagnosis(submission_id=original.submission_id, misconception_code='M02', confidence=.75,
        evidence='2/5', status='provisional', created_at=datetime.now(timezone.utc) + timedelta(seconds=10)))
    db.commit()
    data = client.get(f'/api/classes/{c.id}/misconception-map').json()
    assert data['total_responses'] == 3
    assert sum(item['response_count'] for item in data['concepts']) == 3
    assert next(item for item in data['concepts'] if item['code'] == 'M02')['uncertain'] == 0
