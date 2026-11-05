"""Start a fresh synthetic Fractions demo. Existing paths are never reused/reset."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
from time import monotonic, sleep
from uuid import UUID, uuid5

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import REPOSITORY_ROOT
from app.models import Class, Question, Student, Submission, Teacher
from app.question_catalog import QUESTION_CATALOG
from app.schemas.classroom import AssessmentSubmissionRequest
from app.services.classroom_service import submit_student_assessment
from app.services.dataset_import import import_synthetic_dataset

NAMESPACE = UUID('87e1fa72-7ca6-4ac8-a232-8c2ae19951fd')
APPLICATION_ID = 1330662736
MULTISUBJECT_DATASET = REPOSITORY_ROOT / 'data' / 'multi_subject_synthetic_responses.csv'
OTHER_CLASS_PREFIXES = {
    'Basic algebra': ('Mathematics', 'ALG'),
    'Force and motion': ('Science', 'FM'),
    'Basic electricity': ('Science', 'EL'),
    'Grammar': ('English', 'GR'),
    'Subject-verb agreement': ('English', 'SV'),
}
FRACTIONS_QUESTION_KEYS = ('Q02', 'Q03', 'Q04', 'Q05')
MISCONCEPTION_PATTERNS = {
    'M01': ('Q01', '2/5', 'I added the numerators and denominators to get 2/5.'),
    'M02': ('Q02', '1/8', 'I picked 1/8 because the larger denominator makes it a larger fraction.'),
    'M03': ('Q04', '2/9', 'I did not use a common denominator, so I combined the fractions anyway.'),
    'M04': ('Q03', 'No', 'I think 1/2 and 2/4 are not equivalent because their numbers look different.'),
    'M05': ('Q05', '8/12', 'I changed both fractions to equivalent twelfths, then made an arithmetic error comparing the numerators.'),
}


def expand_fractions_to_40(engine) -> dict[str, int]:
    """Grow the marked demo class to 40 while preserving existing student work."""
    class_id = uuid5(NAMESPACE, 'class')
    with Session(engine, expire_on_commit=False) as db:
        classroom = db.get(Class, class_id)
        if classroom is None or (classroom.subject, classroom.topic) != ('Mathematics', 'Fractions'):
            raise ValueError('The demonstration Fractions class was not found')

        question_rows = {
            question.question_text: question
            for question in db.scalars(
                select(Question).where(
                    Question.subject == 'Mathematics', Question.topic == 'Fractions'
                )
            )
        }
        first_question = question_rows.get('Add 1/2 + 1/3.')
        if first_question is None or first_question.correct_answer != '5/6':
            raise ValueError('The original Fractions question does not match the demo setup')

        questions = {'Q01': first_question}
        for question_key in FRACTIONS_QUESTION_KEYS:
            catalog_question = QUESTION_CATALOG[question_key]
            question = question_rows.get(catalog_question.question_text)
            if question is None:
                question = Question(
                    id=uuid5(NAMESPACE, f'fraction-question:{question_key}'),
                    subject='Mathematics',
                    topic='Fractions',
                    question_text=catalog_question.question_text,
                    correct_answer=catalog_question.correct_answer,
                    explanation_expected=catalog_question.explanation_expected,
                )
                db.add(question)
                question_rows[catalog_question.question_text] = question
            elif question.correct_answer != catalog_question.correct_answer:
                raise ValueError(f'Existing demo question {question_key} has a conflicting answer')
            questions[question_key] = question

        existing_students = list(db.scalars(
            select(Student).where(Student.class_id == classroom.id).order_by(Student.student_code)
        ))
        new_students = []
        existing_codes = {student.student_code for student in existing_students}
        next_number = 4
        while len(existing_students) + len(new_students) < 40 and next_number <= 999:
            code = f'DEMO-{next_number:02d}'
            next_number += 1
            if code in existing_codes:
                continue
            student_id = uuid5(NAMESPACE, f'student:{int(code.removeprefix("DEMO-"))}')
            conflicting_student = db.get(Student, student_id)
            if conflicting_student is not None:
                raise ValueError(f'Student ID for {code} is already used by another class')
            student = Student(id=student_id, class_id=classroom.id, student_code=code)
            db.add(student)
            new_students.append(student)
            existing_codes.add(code)
        if len(existing_students) + len(new_students) < 40:
            raise ValueError('Could not create the remaining demo student codes')

        db.flush()
        db.commit()

        for student in new_students:
            if db.scalar(select(func.count(Submission.id)).where(Submission.student_id == student.id)):
                continue
            student_number = int(student.student_code.removeprefix('DEMO-'))
            target_misconception = f'M{((student_number - 4) % 5) + 1:02d}'
            target_question, wrong_answer, misconception_explanation = MISCONCEPTION_PATTERNS[target_misconception]
            answers = []
            for question_key, question in questions.items():
                if question_key == target_question:
                    answer, explanation = wrong_answer, misconception_explanation
                else:
                    catalog_question = QUESTION_CATALOG.get(question_key)
                    answer = question.correct_answer
                    if question_key == 'Q02':
                        explanation = 'With a numerator of one, a quarter is a larger piece than an eighth.'
                    else:
                        explanation = (
                            catalog_question.explanation_expected
                            if catalog_question
                            else 'I rewrote the fractions with a common denominator and checked the result.'
                        )
                answers.append({
                    'question_id': question.id,
                    'answer': answer,
                    'explanation': explanation,
                })
            submit_student_assessment(db, student.id, AssessmentSubmissionRequest(
                request_id=f'synthetic-40-students:{student.id}', answers=answers,
            ))

        student_count = db.scalar(
            select(func.count(Student.id)).where(Student.class_id == classroom.id)
        ) or 0
        return {'students_created': len(new_students), 'student_count': student_count}


def expand_other_class_rosters_to_40(engine) -> dict[str, int]:
    """Add empty learners to the established non-Fractions demo classes."""
    teacher_id = uuid5(NAMESPACE, 'teacher')
    with Session(engine) as db:
        classes = {
            classroom.topic: classroom
            for classroom in db.scalars(
                select(Class).where(Class.teacher_id == teacher_id)
            )
        }
        rosters = {}
        for topic, (subject, code_prefix) in OTHER_CLASS_PREFIXES.items():
            classroom = classes.get(topic)
            if classroom is None or classroom.subject != subject:
                raise ValueError(f'The demonstration class for {topic} was not found')
            students = list(db.scalars(
                select(Student).where(Student.class_id == classroom.id)
            ))
            student_codes = {student.student_code for student in students}
            numeric_codes = [
                int(code.removeprefix(code_prefix))
                for code in student_codes
                if code.startswith(code_prefix)
                and code.removeprefix(code_prefix).isdigit()
            ]
            next_number = max(numeric_codes, default=0) + 1
            student_count = len(students)
            while student_count < 40:
                code = f'{code_prefix}{next_number:03d}'
                next_number += 1
                if code in student_codes:
                    continue
                student_id = uuid5(NAMESPACE, f'student:{classroom.id}:{code}')
                if db.get(Student, student_id) is not None:
                    raise ValueError(f'Student ID for {code} is already used')
                db.add(Student(
                    id=student_id,
                    class_id=classroom.id,
                    student_code=code,
                ))
                student_count += 1
                student_codes.add(code)
            rosters[topic] = student_count
        db.commit()
        return rosters


def add_classes(directory: Path):
    """Restore sample topics and 40-student rosters in a marked demo only."""
    path = directory.absolute() / 'fractions.sqlite'
    if path.is_symlink() or not path.is_file():
        raise ValueError('A marked demonstration database is required')
    with sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
            raise ValueError('Refusing an unmarked database')
    engine = create_engine(f'sqlite:///{path}')
    try:
        with Session(engine) as db:
            classroom = db.get(Class, uuid5(NAMESPACE, 'class'))
            if (classroom is None or classroom.teacher_id != uuid5(NAMESPACE, 'teacher')
                    or classroom.subject != 'Mathematics' or classroom.topic != 'Fractions'):
                raise ValueError('The demonstration class does not match the expected identity')
        # The importer is transactional and idempotent; existing answers are
        # checked for conflicts and are never replaced.
        with Session(engine) as db:
            imported = import_synthetic_dataset(db, MULTISUBJECT_DATASET, teacher_id=uuid5(NAMESPACE, 'teacher'))
        roster = expand_fractions_to_40(engine)
        roster['class_rosters'] = expand_other_class_rosters_to_40(engine)
        return imported, roster
    finally:
        engine.dispose()


def prepare(directory: Path) -> dict:
    directory = directory.absolute()
    # Atomic mkdir refuses existing files, directories and symlinks. A display
    # name or SQLite marker never authorizes deletion of classroom records.
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    path = directory / 'fractions.sqlite'
    url = f'sqlite:///{path}'
    environment = {**os.environ, 'DATABASE_URL': url, 'APP_ENV': 'development', 'AUTH_MODE': 'demo', 'AI_PROVIDER': 'mock'}
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=REPOSITORY_ROOT / 'backend', env=environment, check=True)
    engine = create_engine(url)
    try:
        with Session(engine, expire_on_commit=False) as db:
            teacher = Teacher(id=uuid5(NAMESPACE, 'teacher'), name='Synthetic demonstration teacher', email='map-demo@example.invalid')
            classroom = Class(id=uuid5(NAMESPACE, 'class'), teacher=teacher,
                class_name='Synthetic Fractions demonstration', subject='Mathematics', topic='Fractions')
            question = Question(id=uuid5(NAMESPACE, 'question'), subject='Mathematics', topic='Fractions',
                question_text='Add 1/2 + 1/3.', correct_answer='5/6', explanation_expected='Explain how you chose equal-sized parts.')
            students = [Student(id=uuid5(NAMESPACE, f'student:{i}'), classroom=classroom, student_code=f'DEMO-{i:02d}') for i in range(1, 4)]
            db.add_all([teacher, classroom, question, *students]); db.commit()
            for student, answer, explanation in [
                (students[1], '2/5', 'I added the numerators and denominators.'),
                (students[2], 'not sure', 'I need help explaining my answer.'),
            ]:
                submit_student_assessment(db, student.id, AssessmentSubmissionRequest(
                    request_id=f'synthetic-preparation:{student.student_code}',
                    answers=[dict(question_id=question.id, answer=answer, explanation=explanation)]))
        context = dict(database=str(path), synthetic=True, class_id=str(classroom.id),
            class_name=classroom.class_name, student_code=students[0].student_code,
            student_id=str(students[0].id), question_id=str(question.id),
            preloaded_responses=2, precomputed_suggestions=0)
        with sqlite3.connect(path) as connection:
            connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
    finally:
        engine.dispose()
    _, roster = add_classes(directory)
    context['student_count'] = roster['student_count']
    context['additional_patterned_students'] = roster['students_created']
    context['preloaded_responses'] += roster['students_created'] * 5
    context['class_rosters'] = {'Fractions': roster['student_count'], **roster['class_rosters']}
    return context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, help='A NEW directory; existing paths are refused')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--add-classes', type=Path,
        help='Restore sample topics and 40-student rosters in an existing marked run')
    parser.add_argument('--api-port', type=int, default=8019)
    parser.add_argument('--web-port', type=int, default=5189)
    args = parser.parse_args()
    if args.add_classes:
        try:
            result = add_classes(args.add_classes)
        except (ValueError, sqlite3.DatabaseError) as error:
            parser.exit(2, f'Could not add classes: {error}\n')
        imported, roster = result
        roster_summary = ', '.join(
            f'{topic}: {count}'
            for topic, count in {
                'Fractions': roster['student_count'], **roster['class_rosters']
            }.items()
        )
        print(f'Additional classes created: {imported.classes_created}; students per class: {roster_summary}; existing responses preserved.')
        return
    if not all(1024 <= port <= 65535 for port in (args.api_port, args.web_port)) or args.api_port == args.web_port:
        parser.error('Choose two distinct ports between 1024 and 65535')
    # mkdtemp reserves a private parent. Each run uses a new, untouched child.
    directory = args.directory or Path(tempfile.mkdtemp(prefix='openpost-map-demo-')) / 'run'
    try:
        context = prepare(directory)
    except FileExistsError:
        parser.exit(2, 'Refusing an existing directory. Start a fresh run; previous classroom/demo records were not changed.\n')
    print(json.dumps(context, indent=2), flush=True)
    if args.prepare_only:
        return
    environment = {**os.environ, 'DATABASE_URL': f'sqlite:///{context["database"]}', 'AI_PROVIDER': 'mock',
        'APP_ENV': 'development', 'AUTH_MODE': 'demo', 'VITE_API_BASE_URL': '/api',
        'CLASS_PULSE_BACKEND_URL': f'http://127.0.0.1:{args.api_port}'}
    frontend = REPOSITORY_ROOT / 'frontend'
    subprocess.run(['npm', 'run', 'build'], cwd=frontend, env=environment, check=True)
    processes = []

    def stop(_signal=None, _frame=None):
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)

    signal.signal(signal.SIGTERM, stop)
    def interrupt(_signal, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, interrupt)
    try:
        # Own the socket before starting Uvicorn. An occupied port must never
        # silently connect the demo frontend to somebody else's database.
        listener = socket.socket()
        listener.bind(('127.0.0.1', args.api_port))
        listener.listen(128)
        try:
            api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--fd', str(listener.fileno())],
                cwd=REPOSITORY_ROOT / 'backend', env=environment, start_new_session=True, pass_fds=(listener.fileno(),))
        finally:
            listener.close()
        processes.append(api)
        deadline = monotonic() + 20
        ready = False
        while monotonic() < deadline and api.poll() is None:
            try:
                ready = httpx.get(f'http://127.0.0.1:{args.api_port}/health', timeout=1).is_success
                if ready:
                    break
            except httpx.HTTPError:
                pass
            sleep(.2)
        if not ready or api.poll() is not None:
            raise RuntimeError('Demo API could not start; check the selected port. Saved synthetic data were retained.')
        web = subprocess.Popen(['npm', 'run', 'preview', '--', '--host', '127.0.0.1', '--port', str(args.web_port), '--strictPort'],
            cwd=frontend, env=environment, start_new_session=True)
        processes.append(web)
        print(f'Open http://127.0.0.1:{args.web_port} · synthetic data · local mock rules · DEMO-01', flush=True)
        print('Fresh run: stop with Ctrl-C and run this command again. No reset/deletion is performed.', flush=True)
        while all(process.poll() is None for process in processes):
            sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == '__main__':
    main()
