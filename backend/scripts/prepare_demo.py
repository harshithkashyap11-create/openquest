"""Initialize an isolated, repeatable synthetic demo. Never resets any database."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from uuid import UUID, uuid5
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.config import REPOSITORY_ROOT
from app.models import Teacher, Class, Student, Question, Submission, Diagnosis
from app.services.learning_service import record_evidence
from app.services.auth_service import provision_account
from app.models.access import AuthAccount

APPLICATION_ID = 1129337156
NAMESPACE = UUID('8ac2d740-c10b-4af5-a79f-f8c9219289bc')
CASES = [
 ('Mathematics','Fractions','M01','Add 1/2 + 1/3.','5/6','2/5','I added the numerators and denominators.'),
 ('Science','Force and motion','FM01','A cart has zero net force on a frictionless track. What happens to its velocity?','Its velocity stays constant.','It stops.','A moving object needs continuing forward force to keep moving.'),
 ('English','Subject-verb agreement','SV01','Choose: The box of pencils (is/are) here.','is','are','Pencils is plural so I chose are, even though box is the subject.'),
]

def stable(key):return uuid5(NAMESPACE,key)


def seed(db):
    teacher=db.get(Teacher,stable('teacher'))
    if teacher is None:
        teacher=Teacher(id=stable('teacher'),name='Synthetic demonstration teacher',email='classpulse-demo@example.invalid')
        db.add(teacher);db.flush()
    contexts=[]
    for subject,topic,code,prompt,expected,answer,explanation in CASES:
        classroom=db.get(Class,stable(subject))
        if classroom is None:
            classroom=Class(id=stable(subject),teacher_id=teacher.id,class_name=f'Synthetic ClassPulse · {subject}',subject=subject,topic=topic)
            db.add(classroom);db.flush()
        question=db.get(Question,stable(f'question:{code}'))
        if question is None:
            question=Question(id=stable(f'question:{code}'),subject=subject,topic=topic,question_text=prompt,correct_answer=expected,explanation_expected='Explain the governing concept and justify the answer.')
            db.add(question);db.flush()
        for ordinal in [1,2]:
            student=db.get(Student,stable(f'student:{code}:{ordinal}'))
            if student is None:
                student=Student(id=stable(f'student:{code}:{ordinal}'),class_id=classroom.id,student_code=f'CP-{code}-{ordinal:02d}')
                db.add(student);db.flush()
            submission=db.get(Submission,stable(f'submission:{code}:{ordinal}'))
            if submission is None:
                submission=Submission(id=stable(f'submission:{code}:{ordinal}'),student_id=student.id,question_id=question.id,attempt_no=1,answer=answer,explanation=explanation)
                db.add(submission);db.flush()
            diagnosis=db.get(Diagnosis,stable(f'diagnosis:{code}:{ordinal}'))
            if diagnosis is None:
                diagnosis=Diagnosis(id=stable(f'diagnosis:{code}:{ordinal}'),submission_id=submission.id,misconception_code=code,confidence=.9,evidence=explanation,provider='mock',status='teacher_reviewed',model_version='synthetic-fixture-v1',misconception_description='Hand-authored synthetic demonstration fixture; not live inference.')
                db.add(diagnosis);db.flush()
            record_evidence(db,student,subject,topic,'diagnosis',f'diagnosis-submission:{submission.id}',{
                'observation_id':f'diagnosis:{diagnosis.id}','diagnosis_id':str(diagnosis.id),'question_id':str(question.id),
                'attempt':'baseline:1','code':code,'correct':False,'uncertain':False,'provider':'mock',
                'model':'synthetic-fixture-v1','evidence':explanation,'fixture':True})
        contexts.append({'subject':subject,'topic':topic,'class_id':str(classroom.id),'student_code':f'CP-{code}-01'})
    db.commit()
    return teacher,contexts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=REPOSITORY_ROOT/'.classpulse-demo')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--with-accounts',action='store_true')
    args=parser.parse_args()
    directory=args.directory.resolve();path=directory/'classpulse-demo.sqlite'
    if path.is_symlink():parser.error('Refusing a symlink database')
    if path.exists():
        with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as connection:
            if connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
                parser.error('Refusing an existing database that is not positively marked as this synthetic demo')
    if args.dry_run:
        print(json.dumps({'dry_run':True,'database':str(path),'action':'additive migration and idempotent synthetic seeding; no reset'}));return
    directory.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'DATABASE_URL':f'sqlite:///{path}','APP_ENV':'test','AUTH_MODE':'demo'}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=REPOSITORY_ROOT/'backend',env=env,check=True)
    with sqlite3.connect(path) as connection:connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
    engine=create_engine(f'sqlite:///{path}')
    with Session(engine,expire_on_commit=False) as db:
        teacher,contexts=seed(db)
        if args.with_accounts:
            credentials={}
            for username,actor in [('demo-teacher',{'teacher_id':teacher.id}),*[(f'demo-student-{c["subject"].lower()}',{'student_id':stable(f'student:{case[2]}:1')}) for c,case in zip(contexts,CASES)]]:
                if not db.scalar(select(AuthAccount.id).where(AuthAccount.username==username)):
                    password=secrets.token_urlsafe(18);provision_account(db,username,password,**actor);credentials[username]=password
            db.commit()
            if credentials:
                destination=directory/'credentials.json'
                descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(descriptor,'w') as file:json.dump(credentials,file,indent=2)
                print('Generated credential file (not printed):',destination)
        print(json.dumps({'database':str(path),'synthetic':True,'contexts':contexts},ensure_ascii=False,indent=2))
    engine.dispose()

if __name__=='__main__':main()
