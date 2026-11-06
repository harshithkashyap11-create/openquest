"""Observable contracts for course entry and the original classroom tools."""
from uuid import uuid4
import base64
import io

import pytest
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.main import app
from app.models import Class, Student, Teacher


@pytest.fixture
def studio_env(db_session):
    teacher = Teacher(name='Demo teacher', email=f'{uuid4()}@example.test')
    classes = [Class(teacher=teacher, class_name=topic, subject=subject, topic=topic)
               for subject, topic in [('Mathematics', 'Fractions'), ('Mathematics', 'Basic algebra'), ('Science', 'Force and motion')]]
    students = [Student(classroom=c, student_code=f'S{i+1:03d}') for c in classes for i in range(2)]
    db_session.add_all([teacher, *classes, *students]); db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client, classes, students
    app.dependency_overrides.clear()


def th(c):
    return {'X-Demo-Role': 'teacher', 'X-Class-ID': str(c.id)}


def sh(s):
    return {'X-Demo-Role': 'student', 'X-Student-ID': str(s.id), 'X-Class-ID': str(s.class_id)}


def questions():
    return [
        {'id': 'choice', 'kind': 'choice', 'text': 'Add 1/2 and 1/3.', 'options': ['2/5', '5/6'], 'answer': 1, 'standard': 'CP.FRACTIONS.ADD', 'explanation': 'Use a common denominator.', 'distractors': {'0': 'Adding denominators'}},
        {'id': 'number', 'kind': 'numeric', 'text': 'Write one half.', 'answer': '0.5', 'standard': 'CP.FRACTIONS.EQUIVALENT'},
        {'id': 'multi', 'kind': 'multiple_select', 'text': 'Select even numbers.', 'options': ['1', '2', '4'], 'answer': [1, 2]},
        {'id': 'boolean', 'kind': 'true_false', 'text': 'A half equals two quarters.', 'options': ['True', 'False'], 'answer': 0},
        {'id': 'short', 'kind': 'short_answer', 'text': 'Name the top number.', 'answer': 'numerator'},
        {'id': 'match', 'kind': 'matching', 'text': 'Match fractions.', 'items': ['1/2', '1/4'], 'options': ['0.25', '0.5'], 'answer': {'1/2': '0.5', '1/4': '0.25'}},
        {'id': 'category', 'kind': 'categorize', 'text': 'Sort numbers.', 'items': ['2', '3'], 'options': ['even', 'odd'], 'answer': {'2': 'even', '3': 'odd'}},
        {'id': 'write', 'kind': 'writing', 'text': 'Explain your approach.', 'points': 2},
    ]


def make_activity(env, qs=None, publish=True):
    client, classes, _ = env
    root = f'/api/classes/{classes[0].id}/studio'
    r = client.post(root + '/activities', headers=th(classes[0]), json={'title': 'Checkpoint', 'questions': qs or questions()})
    assert r.status_code == 201, r.text
    a = r.json()
    if publish:
        r = client.post(root + f'/activities/{a["id"]}/publish', headers=th(classes[0])); assert r.status_code == 200, r.text
    return a


def submit(env, a, answers=None, request_id=None):
    client, _, students = env
    return client.post(f'/api/students/{students[0].id}/studio/activities/{a["id"]}/submit', headers=sh(students[0]), json={
        'request_id': request_id or str(uuid4()),
        'answers': answers or {'choice': 0, 'number': '1/2', 'multi': [2, 1], 'boolean': 0, 'short': ' Numerator ', 'match': {'1/2': '0.5', '1/4': '0.25'}, 'category': {'2': 'even', '3': 'odd'}, 'write': 'I used equivalent fractions.'},
        'reasoning': {'choice': 'I added the denominators.'},
        'media': {'write': {'strokes': [[[10, 10], [20, 20]]]}} if any(q['id'] == 'write' for q in a['questions']) else {},
    })


@pytest.mark.parametrize('password', ['*', 'a', 'anything'])
def test_demo_login_accepts_any_password_and_filters_teacher_courses(studio_env, password):
    client, _, _ = studio_env
    r = client.post('/api/auth/demo-login', json={'role': 'teacher', 'username': 'math1', 'password': password})
    assert r.status_code == 200, r.text
    assert len(r.json()['courses']) == 2
    assert {c['subject'] for c in r.json()['courses']} == {'Mathematics'}


def test_student_alias_returns_actual_class_bound_records(studio_env):
    client, _, students = studio_env
    r = client.post('/api/auth/demo-login', json={'role': 'student', 'username': 'student1', 'password': '*'})
    assert r.status_code == 200, r.text
    assert len(r.json()['courses']) == 3
    assert r.json()['courses'][0]['student_id'] in {str(s.id) for s in students}
    assert client.post('/api/auth/demo-login', json={'role': 'student', 'username': 'S999', 'password': 'a'}).status_code == 404


def test_publication_grading_retry_and_manual_review(studio_env):
    client, classes, students = studio_env
    a = make_activity(studio_env)
    student_url = f'/api/students/{students[0].id}/studio/activities/{a["id"]}'
    delivered = client.get(student_url, headers=sh(students[0])).json()
    assert 'answer' not in delivered['questions'][0]
    assert 'distractors' not in delivered['questions'][0]
    assert client.patch(f'/api/classes/{classes[0].id}/studio/activities/{a["id"]}', headers=th(classes[0]), json={'title': 'Changed', 'questions': questions()}).status_code == 409
    rid = str(uuid4()); first = submit(studio_env, a, request_id=rid)
    assert first.status_code == 201, first.text
    work = first.json()
    assert work['score'] == 6 and work['possible'] == 9 and work['pending_review'] == 1
    assert work['results']['choice']['signal'] == 'Adding denominators'
    assert work['results']['number']['correct'] is True
    assert submit(studio_env, a, request_id=rid).json()['id'] == work['id']
    review = client.patch(f'/api/classes/{classes[0].id}/studio/work/{work["id"]}/grade', headers=th(classes[0]), json={'question_id': 'write', 'points': 2, 'comment': 'Clear reasoning.'})
    assert review.status_code == 200, review.text
    assert review.json()['score'] == 8 and review.json()['pending_review'] == 0
    report = client.get(f'/api/classes/{classes[0].id}/studio/report', headers=th(classes[0])).json()
    assert report['submitted_students'] == 1
    assert next(s for s in report['standards'] if s['standard'] == 'CP.FRACTIONS.ADD')['earned'] == 0
    assert client.get(f'/api/students/{students[-1].id}/studio/activities/{a["id"]}', headers=sh(students[-1])).status_code == 404


def test_sets_enforce_progression_on_server(studio_env):
    client, classes, students = studio_env
    a = make_activity(studio_env, questions()[:1]); b = make_activity(studio_env, questions()[:1])
    root = f'/api/classes/{classes[0].id}/studio'
    r = client.post(root + '/sets', headers=th(classes[0]), json={'title': 'Fractions pathway', 'activity_ids': [a['id'], b['id']], 'minimum_percent': 80})
    assert r.status_code == 201, r.text
    url = f'/api/students/{students[0].id}/studio/activities/{b["id"]}/submit'
    payload = {'request_id': str(uuid4()), 'answers': {'choice': 1}}
    assert client.post(url, headers=sh(students[0]), json=payload).status_code == 409
    assert submit(studio_env, a, answers={'choice': 1}).status_code == 201
    assert client.post(url, headers=sh(students[0]), json=payload).status_code == 201


def test_qr_answers_replace_with_actual_counts(studio_env):
    client, classes, students = studio_env
    a = make_activity(studio_env, questions()[:1]); root = f'/api/classes/{classes[0].id}/studio'
    roster = client.get(root + '/roster', headers=th(classes[0]))
    assert roster.status_code == 200 and len(roster.json()) == 2
    r = client.post(root + '/qr-sessions', headers=th(classes[0]), json={'activity_id': a['id'], 'question_id': 'choice'})
    assert r.status_code == 201, r.text
    url = root + '/qr-sessions/' + r.json()['id']
    for answer in [0, 1]:
        r = client.post(url + '/responses', headers=th(classes[0]), json={'student_id': str(students[0].id), 'option': answer})
        assert r.status_code == 200, r.text
    assert r.json()['counts'] == [0, 1] and r.json()['responded'] == 1
    assert client.post(url + '/responses', headers=th(classes[0]), json={'student_id': str(students[-1].id), 'option': 1}).status_code == 403


def test_exports_are_readable_and_csv_cells_are_safe(studio_env):
    client, classes, _ = studio_env
    a = make_activity(studio_env); w = submit(studio_env, a).json()
    root = f'/api/classes/{classes[0].id}/studio'
    pdf = client.get(root + f'/work/{w["id"]}/export.pdf', headers=th(classes[0]))
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    from pypdf import PdfReader
    extracted = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert 'Answer: 2/5' in extracted
    csv = client.get(root + '/grades.csv', headers=th(classes[0]))
    assert csv.status_code == 200 and 'Checkpoint' in csv.text and 'S001' in csv.text


def test_pdf_import_previews_without_saving(studio_env):
    from reportlab.pdfgen import canvas
    client, classes, _ = studio_env
    data = io.BytesIO(); pdf = canvas.Canvas(data)
    text = pdf.beginText(40, 780)
    for line in ['1. What is 1/2 + 1/3?', 'A. 2/5', 'B. 5/6', 'Answer: B', 'Explanation: Use a common denominator.']:
        text.textLine(line)
    pdf.drawText(text); pdf.save()
    r = client.post(f'/api/classes/{classes[0].id}/studio/import-pdf', headers=th(classes[0]), json={'filename': 'questions.pdf', 'content_base64': base64.b64encode(data.getvalue()).decode()})
    assert r.status_code == 200, r.text
    assert r.json()['questions'][0]['answer'] == 1
    assert client.get(f'/api/classes/{classes[0].id}/studio/activities', headers=th(classes[0])).json() == []


def test_bank_generation_and_feedback_preserve_original_sources(studio_env):
    client, classes, students = studio_env
    root = f'/api/classes/{classes[0].id}/studio'
    bank = client.get(root + '/library?q=denominator', headers=th(classes[0]))
    assert bank.status_code == 200, bank.text
    assert bank.json() and all('denominator' in str(q).lower() for q in bank.json())
    generated = client.post(root + '/generate', headers=th(classes[0]), json={'topic': 'Fractions', 'count': 2, 'kind': 'choice'})
    assert generated.status_code == 200, generated.text
    assert len(generated.json()['questions']) == 2 and generated.json()['provider'] == 'template'
    a = make_activity(studio_env); w = submit(studio_env, a).json()
    url = f'/api/students/{students[0].id}/studio/work/{w["id"]}/feedback'
    r = client.post(url, headers=sh(students[0]), json={'question_id': 'choice', 'message': 'I added the denominators.', 'language': 'en'})
    assert r.status_code == 200, r.text
    assert r.json()['feedback']['provider'] == 'template'
    assert r.json()['feedback']['evidence'] == 'I added the denominators.'
    delivered = client.get(f'/api/students/{students[0].id}/studio/activities/{a["id"]}', headers=sh(students[0])).json()
    assert len(delivered['attempts'][0]['conversations']['choice']) == 2


def test_invalid_answers_media_and_attempt_limits(studio_env):
    client, classes, students = studio_env
    a = make_activity(studio_env, questions()[:1])
    url = f'/api/students/{students[0].id}/studio/activities/{a["id"]}/submit'
    for _ in range(3):
        assert submit(studio_env, a, answers={'choice': 1}).status_code == 201
    assert submit(studio_env, a, answers={'choice': 1}).status_code == 409
    b = make_activity(studio_env, questions()[:1])
    bad = client.post(f'/api/students/{students[0].id}/studio/activities/{b["id"]}/submit', headers=sh(students[0]), json={'request_id': str(uuid4()), 'answers': {'choice': 1}, 'media': {'choice': {'strokes': [[[1, -20]]]}}})
    assert bad.status_code == 422


def test_copilot_context_includes_studio_counts_without_media(studio_env):
    from app.services.copilot_context import extract_classroom_context
    client, classes, _ = studio_env
    a = make_activity(studio_env); submit(studio_env, a)
    db = app.dependency_overrides[get_db]()
    summary, grounding = extract_classroom_context(db, classes[0].id)
    assert summary.studio_report['submitted_students'] == 1
    assert 'CLASSROOM STUDIO' in grounding
    assert 'CP.FRACTIONS.ADD' in grounding
    assert 'strokes' not in str(summary.studio_report)
    assert 'I added the denominators.' not in str(summary.studio_report)


def test_grade_csv_uses_latest_attempt_and_escapes_formula_titles(studio_env):
    import csv
    client, classes, students = studio_env
    a = make_activity(studio_env, questions()[:1], publish=False)
    root = f'/api/classes/{classes[0].id}/studio'
    client.patch(root + '/activities/' + a['id'], headers=th(classes[0]), json={'title': '=danger()', 'questions': questions()[:1]})
    client.post(root + '/activities/' + a['id'] + '/publish', headers=th(classes[0]))
    submit(studio_env, a, answers={'choice': 0}); submit(studio_env, a, answers={'choice': 1})
    rows = list(csv.DictReader(io.StringIO(client.get(root + '/grades.csv', headers=th(classes[0])).text)))
    assert len(rows) == 1
    assert rows[0]['activity'] == "'=danger()" and rows[0]['earned'] == '1' and rows[0]['attempt'] == '2'


def test_invalid_choice_is_rejected_without_consuming_attempt(studio_env):
    client, classes, students = studio_env
    a = make_activity(studio_env, questions()[:1])
    assert submit(studio_env, a, answers={'choice': 99}).status_code == 422
    assert submit(studio_env, a, answers={'choice': True}).status_code == 422
    assert submit(studio_env, a, answers={'choice': 1}).json()['attempt'] == 1


def test_drawing_is_rendered_as_a_png_for_multimodal_feedback():
    from app.services.studio_media import media_parts
    from PIL import Image
    parts = media_parts({'strokes': [[[10, 10], [120, 100]]]})
    assert parts[0]['mimeType'] == 'image/png'
    image = Image.open(io.BytesIO(base64.b64decode(parts[0]['data'])))
    assert image.size == (800, 320)
    assert image.getpixel((60, 51)) != (255, 255, 255)


def test_teacher_authored_bank_questions_persist_and_can_be_searched(studio_env):
    client, classes, _ = studio_env
    root = f'/api/classes/{classes[0].id}/studio'
    question = {**questions()[0], 'text': 'Custom diagnostic item about thirds'}
    r = client.post(root + '/library', headers=th(classes[0]), json=question)
    assert r.status_code == 201, r.text
    rows = client.get(root + '/library?q=Custom', headers=th(classes[0])).json()
    assert len(rows) == 1 and rows[0]['text'] == 'Custom diagnostic item about thirds'
