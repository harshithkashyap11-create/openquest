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
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import REPOSITORY_ROOT
from app.models import Class, Question, Student, Teacher
from app.schemas.classroom import AssessmentSubmissionRequest
from app.services.classroom_service import submit_student_assessment
from app.services.dataset_import import import_synthetic_dataset

NAMESPACE = UUID('87e1fa72-7ca6-4ac8-a232-8c2ae19951fd')
APPLICATION_ID = 1330662736
MULTISUBJECT_DATASET = REPOSITORY_ROOT / 'data' / 'multi_subject_synthetic_responses.csv'


def add_classes(directory: Path):
    """Add the established sample topics to this application's marked demo only."""
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
            return import_synthetic_dataset(db, MULTISUBJECT_DATASET, teacher_id=uuid5(NAMESPACE, 'teacher'))
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
    add_classes(directory)
    return context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, help='A NEW directory; existing paths are refused')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--add-classes', type=Path, help='Add the other sample topics to an existing marked run')
    parser.add_argument('--api-port', type=int, default=8019)
    parser.add_argument('--web-port', type=int, default=5189)
    args = parser.parse_args()
    if args.add_classes:
        try:
            result = add_classes(args.add_classes)
        except (ValueError, sqlite3.DatabaseError) as error:
            parser.exit(2, f'Could not add classes: {error}\n')
        print(f'Additional classes created: {result.classes_created}; existing responses preserved.')
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
