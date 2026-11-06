import json
from types import SimpleNamespace
import httpx
from app.models.studio import StudioWork
from test_classroom_studio import studio_env, make_activity, questions, submit, th


def test_lms_passback_uses_final_grade_and_keeps_delivery_receipt(studio_env, monkeypatch):
    from app.services import studio_lms as lms
    client, classes, students = studio_env
    a = make_activity(studio_env, questions()[:1]); result = submit(studio_env, a, answers={'choice': 1}).json()
    from app.main import app
    from app.core.database import get_db
    from uuid import UUID
    db = app.dependency_overrides[get_db](); work = db.get(StudioWork, UUID(result['id']))
    settings = SimpleNamespace(lms_access_token='test-only-token', lms_lineitems={a['id']: 'https://lms.example.test/lineitems/1'}, lms_user_ids={str(students[0].id): 'learner-lti-42'}, lms_auto_passback=True)
    monkeypatch.setattr(lms, 'get_settings', lambda: settings)
    calls = []
    def handler(request):
        body = json.loads(request.content)
        assert str(request.url) == 'https://lms.example.test/lineitems/1/scores'
        assert request.headers['Content-Type'] == 'application/vnd.ims.lis.v1.score+json'
        assert body['scoreGiven'] == 1 and body['scoreMaximum'] == 1
        assert body['userId'] == 'learner-lti-42' and body['gradingProgress'] == 'FullyGraded'
        calls.append(body)
        return httpx.Response(204)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        assert lms.send_score(db, work, client=http)['status'] == 'sent'
        assert lms.send_score(db, work, client=http)['status'] == 'sent'
    assert len(calls) == 1
    db.expire(work); assert work.lms_receipt['status'] == 'sent'


def test_missing_lms_configuration_preserves_submitted_grade(studio_env):
    client, classes, _ = studio_env
    a = make_activity(studio_env, questions()[:1]); work = submit(studio_env, a, answers={'choice': 1}).json()
    root = f'/api/classes/{classes[0].id}/studio'
    response = client.post(root + f'/work/{work["id"]}/passback', headers=th(classes[0]))
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'not_configured'
    assert work['score'] == 1
