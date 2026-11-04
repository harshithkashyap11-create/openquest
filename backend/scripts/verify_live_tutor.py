"""Opt-in response-aware live tutor smoke using only an isolated synthetic learner."""
import argparse,json
from pathlib import Path
from time import perf_counter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.models import Base, Teacher, Class, Student, Intervention, InterventionAssignment
from app.core.database import get_db
from app.services.intervention_service import INTERVENTION_TEMPLATES


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not args.live:parser.error('--live is required')
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(engine)
    report={'synthetic':True,'cases':[]}
    with Session(engine,expire_on_commit=False) as db:
        classroom=Class(class_name='Synthetic tutor check',teacher=Teacher(name='Synthetic teacher',email='tutor-smoke@test.invalid'))
        student=Student(classroom=classroom,student_code='SYNTHETIC_TUTOR');db.add(student);db.flush()
        t=INTERVENTION_TEMPLATES['M01']
        intervention=Intervention(subject='Mathematics',topic='Fractions',misconception_code='M01',**{k:getattr(t,k) for k in ['title','instructions','learning_objective','explanation','introduction','guided_example']},practice_questions=list(t.practice_questions),expected_answers=list(t.expected_answers),hints=list(t.hints),provider='template')
        db.add(intervention);db.flush();assignment=InterventionAssignment(intervention_id=intervention.id,student_id=student.id);db.add(assignment);db.commit()
        app.dependency_overrides[get_db]=lambda:db
        try:
            with TestClient(app) as client:
                for ordinal,response in enumerate(['','I will use equal-sized parts and rewrite both fractions with denominator 12.']):
                    start=perf_counter();r=client.post(f'/api/intervention-assignments/{assignment.id}/tutor/hints',headers={'X-Demo-Role':'student','X-Student-ID':str(student.id)},json={'request_id':f'live-tutor-smoke-{ordinal}','question_index':0,'generation_mode':'live','language':'te','response':response})
                    report['cases'].append({'http_status':r.status_code,'latency_ms':round((perf_counter()-start)*1000),'result':r.json()})
        finally:app.dependency_overrides.clear()
    engine.dispose();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':[{k:v for k,v in c.items() if k!='result'} for c in report['cases']]}))

if __name__=='__main__':main()
