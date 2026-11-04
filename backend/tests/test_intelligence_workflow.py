from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import get_db
from app.models import Teacher, Class, Student, Question, Submission, Diagnosis
from app.models.learning import LearningEvent


def test_entire_assessment_approval_tutoring_reassessment_cycle(db_session):
    classroom = Class(teacher=Teacher(name='Cycle teacher', email='cycle@test.invalid'), class_name='Cycle fractions')
    students = [Student(classroom=classroom, student_code=f'CYCLE{i}') for i in range(2)]
    question = Question(topic='Fractions', question_text='Add 1/2 + 1/3.', correct_answer='5/6')
    db_session.add_all([*students, question])
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            th = {'X-Demo-Role': 'teacher', 'X-Class-ID': str(classroom.id)}
            for student in students:
                sh = {'X-Demo-Role': 'student', 'X-Student-ID': str(student.id)}
                url = f'/api/students/{student.id}/assessment-submissions'
                payload = {'request_id': f'cycle-{student.student_code}', 'answers': [{'question_id': str(question.id), 'answer': '2/5', 'explanation': 'I added the numerators and denominators.'}]}
                assert client.post(url, json=payload, headers=sh).status_code == 201
                assert client.post(url, json=payload, headers=sh).json()['attempt_no'] == 1
            outcome = client.post(f'/api/classes/{classroom.id}/diagnose', headers=th)
            assert outcome.status_code == 200, outcome.text
            assert db_session.query(Submission).count() == 2
            assert db_session.query(Diagnosis).count() == 2
            group = client.post(f'/api/classes/{classroom.id}/groups/generate', headers=th).json()['groups'][0]
            assert client.post(f'/api/groups/{group["id"]}/interventions/generate', headers=th).status_code == 409
            client.patch(f'/api/groups/{group["id"]}/review', json={'status': 'approved'}, headers=th)
            generated = client.post(f'/api/groups/{group["id"]}/interventions/generate', headers=th)
            assert generated.status_code == 200, generated.text
            assignment = next(x for x in generated.json()['assignments'] if x['student_id'] == str(students[0].id))
            aid = assignment['id']
            sh = {'X-Demo-Role': 'student', 'X-Student-ID': str(students[0].id)}
            assert client.post(f'/api/intervention-assignments/{aid}/tutor/hints', headers=sh,
                json={'request_id': 'cycle-hint-request', 'question_index': 0}).status_code == 200
            assert client.post(f'/api/intervention-assignments/{aid}/submit', headers=sh,
                json={'answers': [{'question_index': i, 'answer': a} for i, a in enumerate(['5/12', '1/2', '7/8'])]}).status_code == 200
            completed = client.post(f'/api/intervention-assignments/{aid}/complete', headers=sh)
            assert completed.status_code == 200, completed.text
            rid = completed.json()['reassessment']['id']
            questions = completed.json()['reassessment']['questions']
            answer_map = {q.id: q.correct_answer for q in db_session.scalars(select(Question))}
            payload = {'answers': [{'question_id': q['id'], 'answer': answer_map[next(k for k in answer_map if str(k) == q['id'])]} for q in questions]}
            result = client.post(f'/api/reassessments/{rid}/submit', headers=sh, json=payload)
            assert result.status_code == 200, result.text
            state = client.get(f'/api/students/{students[0].id}/learning-state', headers=sh).json()[0]
            assert state['session_state'] == 'COMPLETED'
            assert state['hint_count'] == 1
            assert state['active_misconceptions'] == []
            assert state['independent_evidence_count'] == 4
            assert any(e['kind'] == 'reassessment' for e in state['events'])
            assert len(client.get(f'/api/classes/{classroom.id}/learning-states', headers=th).json()) == 2
    finally:
        app.dependency_overrides.clear()
