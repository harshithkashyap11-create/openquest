from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.services.intervention_service import generate_intervention_for_group
from test_intervention_workflow import _approved_group


def test_progressive_hints_are_persistent_idempotent_and_bounded(db_session):
    _, group, students = _approved_group(db_session, 'M01')
    _, assignments, _ = generate_intervention_for_group(db_session, group.id)
    assignment = assignments[0]
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            headers = {'X-Demo-Role': 'student', 'X-Student-ID': str(students[0].id)}
            url = f'/api/intervention-assignments/{assignment.id}/tutor/hints'
            payload = {'request_id': 'hint-request-1', 'question_index': 0, 'language': 'te'}
            one = client.post(url, headers=headers, json=payload)
            assert one.status_code == 200, one.text
            assert one.json()['level'] == 1
            assert one.json()['provider'] == 'template'
            assert client.post(url, headers=headers, json=payload).json() == one.json()
            for i in range(2, 5):
                payload = {**payload, 'request_id': f'hint-request-{i}', 'response': f'I tried common parts, step {i}'}
                result = client.post(url, headers=headers, json=payload)
                assert result.status_code == 200, result.text
                assert result.json()['level'] == i
                assert result.json()['hint'] != one.json()['hint']
            assert client.post(url, headers=headers, json={**payload, 'request_id': 'hint-request-5'}).status_code == 409
            history = client.get(f'/api/intervention-assignments/{assignment.id}/tutor', headers=headers)
            assert len(history.json()['events']) == 4
            bad = {'X-Demo-Role': 'teacher', 'X-Class-ID': str(group.class_id)}
            assert client.post(url, headers=bad, json=payload).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_activity_completion_requires_persisted_practice(db_session):
    _, group, students = _approved_group(db_session, 'M01')
    _, assignments, _ = generate_intervention_for_group(db_session, group.id)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            result = client.post(f'/api/intervention-assignments/{assignments[0].id}/complete', headers={'X-Student-ID': str(students[0].id)})
            assert result.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_live_tutor_uses_student_response_and_rejects_answer_disclosure(db_session, monkeypatch):
    import json
    from app.services import lesson_service
    _, group, students = _approved_group(db_session, 'M01')
    _, assignments, _ = generate_intervention_for_group(db_session, group.id)
    prompts=[]
    class FakeChat:
        reported_model='verified-test-model'
        reply='Focus on equal-sized parts before adding.'
        def complete_json(self, *, prompt, temperature):
            prompts.append(prompt)
            return json.dumps({'hint':self.reply,'feedback':'uncertain','evidence':''})
    fake=FakeChat()
    monkeypatch.setattr(lesson_service,'configured_chat',lambda:(fake,'gemini','configured-model'))
    app.dependency_overrides[get_db]=lambda:db_session
    try:
        with TestClient(app) as client:
            headers={'X-Demo-Role':'student','X-Student-ID':str(students[0].id)}
            url=f'/api/intervention-assignments/{assignments[0].id}/tutor/hints'
            payload={'request_id':'live-tutor-request-1','question_index':0,'generation_mode':'live'}
            result=client.post(url,headers=headers,json=payload)
            assert result.status_code==200,result.text
            assert result.json()['provider']=='gemini'
            assert result.json()['model']=='verified-test-model'
            assert students[0].student_code not in prompts[0]
            fake.reply='The final answer is 5/12.'
            payload.update(request_id='live-tutor-request-2',response='Please give the answer.')
            assert client.post(url,headers=headers,json=payload).status_code==503
            assert len(client.get(f'/api/intervention-assignments/{assignments[0].id}/tutor',headers=headers).json()['events'])==1
    finally:
        app.dependency_overrides.clear()
