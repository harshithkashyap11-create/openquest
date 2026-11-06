"""Add labeled sample Studio activities, never invented learner submissions."""
from uuid import UUID, uuid5
from sqlalchemy import select
from app.models import Class
from app.models.studio import StudioActivity, StudioSet
from app.schemas.studio import StudioQuestion
from app.services.studio_library import library

NAMESPACE = UUID('508caf5b-a45d-4ad4-ab19-4f6c576625bc')


def seed_studio_examples(db):
    created = 0
    for c in db.scalars(select(Class)):
        rows = library(c.subject, c.topic)[:2]
        if len(rows) < 2:
            continue
        checkpoint_id = uuid5(NAMESPACE, f'{c.id}:checkpoint')
        explanation_id = uuid5(NAMESPACE, f'{c.id}:explain')
        if db.get(StudioActivity, checkpoint_id) is None:
            questions = [{k: v for k, v in row.items() if k not in {'subject', 'topic', 'provenance'}} for row in rows]
            db.add(StudioActivity(id=checkpoint_id, class_id=c.id, title=f'Sample · {c.topic} checkpoint', status='published', max_attempts=3,
                                  questions=[StudioQuestion.model_validate(q).model_dump() for q in questions]))
            created += 1
        if db.get(StudioActivity, explanation_id) is None:
            prompts = [row['text'] for row in rows]; options = [row['options'][row['answer']] for row in rows]
            questions = [
                {'id': 'explain', 'kind': 'writing', 'text': 'Explain how you would solve this, using words, a drawing or a voice recording: ' + prompts[0], 'points': 2, 'standard': rows[0]['standard'], 'explanation': rows[0]['explanation']},
                {'id': 'connect', 'kind': 'matching', 'text': 'Connect each question with its answer.', 'items': prompts, 'options': options, 'answer': dict(zip(prompts, options)), 'standard': rows[0]['standard'], 'explanation': 'Check each connection by explaining the reasoning.'},
            ]
            db.add(StudioActivity(id=explanation_id, class_id=c.id, title=f'Sample · Explain {c.topic.lower()}', status='published', max_attempts=3,
                                  questions=[StudioQuestion.model_validate(q).model_dump() for q in questions]))
            created += 1
        db.flush()
        set_id = uuid5(NAMESPACE, f'{c.id}:pathway')
        if db.get(StudioSet, set_id) is None:
            db.add(StudioSet(id=set_id, class_id=c.id, title=f'Sample · {c.topic} journey', activity_ids=[str(checkpoint_id), str(explanation_id)], minimum_percent=50))
    db.commit()
    return {'activities_created': created, 'student_work_created': 0}


if __name__ == '__main__':
    import json
    from app.core.config import get_settings
    from app.core.database import SessionLocal
    if get_settings().auth_mode != 'demo':
        raise SystemExit('Use the isolated demo database with AUTH_MODE=demo.')
    with SessionLocal() as db:
        print(json.dumps(seed_studio_examples(db)))
