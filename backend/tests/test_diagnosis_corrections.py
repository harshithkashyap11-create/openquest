from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import get_db
from app.models import Teacher, Class, Diagnosis
from test_grouping_service import _add_diagnosis
from app.services.grouping_service import generate_proposed_groups


def test_correction_preserves_original_and_changes_next_group_proposal(db_session):
    classroom = Class(class_name='Correction demo', teacher=Teacher(name='Teacher', email='correction@test.invalid'))
    db_session.add(classroom); db_session.flush()
    first = _add_diagnosis(db_session, classroom, 'M01', .9, 'CORR1')
    _add_diagnosis(db_session, classroom, 'M01', .9, 'CORR2')
    diagnosis = db_session.scalar(select(Diagnosis).where(Diagnosis.submission.has(student_id=first.id)))
    db_session.commit()
    assert len(generate_proposed_groups(db_session, classroom.id)) == 1
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            headers = {'X-Demo-Role': 'teacher', 'X-Class-ID': str(classroom.id)}
            url = f'/api/diagnoses/{diagnosis.id}/corrections'
            payload = {'code':'CORRECT', 'reason':'Reviewed reasoning with learner.', 'expected_version':0, 'request_id':'correction-request-1'}
            saved = client.post(url, headers=headers, json=payload)
            assert saved.status_code == 200, saved.text
            assert client.post(url, headers=headers, json=payload).json() == saved.json()
            assert diagnosis.misconception_code == 'M01'
            assert len(client.get(url, headers=headers).json()) == 1
            assert generate_proposed_groups(db_session, classroom.id) == []
            payload['request_id'] = 'correction-request-2'
            assert client.post(url, headers=headers, json=payload).status_code == 409
    finally:
        app.dependency_overrides.clear()
