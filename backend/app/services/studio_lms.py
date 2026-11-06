"""Configured LTI AGS score publishing; no LMS launch/token provisioning is implied.

Protocol: https://www.imsglobal.org/spec/lti-ags/v2p0/#score-publish-service
"""
from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import urlsplit
import httpx
from sqlalchemy import select
from app.core.config import get_settings
from app.models.studio import StudioWork


def integration_status(db, class_id):
    from app.models.studio import StudioActivity
    from app.models import Student
    settings = get_settings()
    activities = list(db.scalars(select(StudioActivity.id).where(StudioActivity.class_id == class_id)))
    students = list(db.scalars(select(Student.id).where(Student.class_id == class_id)))
    return {'automatic': settings.lms_auto_passback, 'token_configured': bool(settings.lms_access_token),
            'mapped_activities': sum(str(a) in settings.lms_lineitems for a in activities),
            'mapped_students': sum(str(s) in settings.lms_user_ids for s in students)}


def send_score(db, w, client=None):
    from app.services.studio_service import work_view
    settings = get_settings(); endpoint = settings.lms_lineitems.get(str(w.activity_id)); user = settings.lms_user_ids.get(str(w.student_id))
    if not endpoint or not user or not settings.lms_access_token:
        return {'status': 'not_configured'}
    if urlsplit(endpoint).scheme != 'https' or not urlsplit(endpoint).netloc or urlsplit(endpoint).username:
        return {'status': 'invalid_configuration'}
    newer = db.scalar(select(StudioWork.id).where(StudioWork.student_id == w.student_id, StudioWork.activity_id == w.activity_id, StudioWork.attempt > w.attempt).limit(1))
    if newer:
        return {'status': 'superseded'}
    view = work_view(w)
    if view['pending_review']:
        return {'status': 'pending_review'}
    fingerprint = hashlib.sha256(json.dumps([view['score'], view['possible']]).encode()).hexdigest()
    receipt = w.lms_receipt or {}
    if receipt.get('fingerprint') == fingerprint and receipt.get('status') == 'sent':
        return receipt
    timestamp = receipt.get('timestamp') if receipt.get('fingerprint') == fingerprint else datetime.now(timezone.utc).isoformat()
    payload = {'timestamp': timestamp, 'scoreGiven': view['score'], 'scoreMaximum': view['possible'], 'activityProgress': 'Completed', 'gradingProgress': 'FullyGraded', 'userId': user}
    headers = {'Authorization': f'Bearer {settings.lms_access_token}', 'Content-Type': 'application/vnd.ims.lis.v1.score+json'}
    try:
        if client:
            response = client.post(endpoint.rstrip('/') + '/scores', json=payload, headers=headers, timeout=10)
        else:
            with httpx.Client(follow_redirects=False, timeout=10) as http:
                response = http.post(endpoint.rstrip('/') + '/scores', json=payload, headers=headers)
        status = 'sent' if 200 <= response.status_code < 300 else 'failed'
    except httpx.HTTPError:
        status = 'retry_needed'
    # Do not store upstream bodies, tokens or URLs with the learner's record.
    w.lms_receipt = {'status': status, 'timestamp': timestamp, 'fingerprint': fingerprint}
    db.commit()
    return w.lms_receipt


def maybe_passback(db, work):
    if get_settings().lms_auto_passback:
        send_score(db, work)
