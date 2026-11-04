"""Generate three synthetic M01 lesson drafts in an isolated in-memory database."""
import argparse, json, tempfile
from pathlib import Path
from time import perf_counter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import get_db
from app.core.config import get_settings
from app.main import app
from app.models import Base, Class, Teacher, Student


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.live:parser.error('--live is required to authorize three provider requests')
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    report={'provider':get_settings().ai_provider,'synthetic':True,'cases':[]}
    with Session(engine,expire_on_commit=False) as db:
        classroom=Class(class_name='Synthetic live lesson check',teacher=Teacher(name='Synthetic teacher',email='live-lesson@test.invalid'))
        db.add(Student(classroom=classroom,student_code='LIVE_SYNTHETIC'));db.commit()
        app.dependency_overrides[get_db]=lambda:db
        try:
            with TestClient(app) as client:
                for language in ['en','hi','te']:
                    start=perf_counter()
                    result=client.post(f'/api/classes/{classroom.id}/lessons/generate',headers={'X-Demo-Role':'teacher','X-Class-ID':str(classroom.id)},json={'misconception_code':'M01','language':language,'request_id':f'live-lesson-{language}'})
                    report['cases'].append({'language':language,'http_status':result.status_code,'latency_ms':round((perf_counter()-start)*1000),'lesson':result.json()})
        finally:app.dependency_overrides.clear()
    engine.dispose()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'provider':report['provider'],'cases':[{k:v for k,v in c.items() if k!='lesson'} for c in report['cases']]}))

if __name__=='__main__':main()
