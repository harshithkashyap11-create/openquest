from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models import PracticeResponse
from app.services.intervention_service import generate_intervention_for_group
from test_intervention_workflow import _approved_group


def test_sync_practice_is_atomic_idempotent_and_checks_revision(db_session):
    _, group, students = _approved_group(db_session, 'M01')
    intervention, assignments, _ = generate_intervention_for_group(db_session, group.id)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            headers = {'X-Demo-Role': 'student', 'X-Student-ID': str(students[0].id)}
            url = f'/api/intervention-assignments/{assignments[0].id}/sync-practice'
            payload = {'request_id': 'offline-command-1', 'intervention_id': str(intervention.id), 'answers': [{'question_index': 0, 'answer': '5/12'}]}
            first = client.post(url, headers=headers, json=payload)
            assert first.status_code == 200, first.text
            assert client.post(url, headers=headers, json=payload).json() == first.json()
            assert db_session.query(PracticeResponse).count() == 1
            payload['answers'][0]['answer'] = '2/10'
            assert client.post(url, headers=headers, json=payload).status_code == 409
    finally:
        app.dependency_overrides.clear()
