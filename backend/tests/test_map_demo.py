import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from app.services.diagnosis_provider import RuleBasedDiagnosisProvider

BACKEND = Path(__file__).resolve().parents[1]


def prepare(directory):
    return subprocess.run([sys.executable, '-m', 'scripts.run_map_demo', '--prepare-only', '--directory', str(directory)],
        cwd=BACKEND, env={**os.environ, 'AI_PROVIDER': 'mock', 'AUTH_MODE': 'demo', 'APP_ENV': 'test'}, capture_output=True, text=True)


def test_fresh_demo_includes_all_previously_available_topics_without_precomputed_suggestions(tmp_path):
    target = tmp_path / 'new-run'
    result = prepare(target)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(target / 'fractions.sqlite') as db:
        assert db.execute('SELECT count(*) FROM diagnoses').fetchone()[0] == 0
        assert set(db.execute('SELECT subject, topic FROM classes')) == {
            ('Mathematics', 'Fractions'), ('Mathematics', 'Basic algebra'),
            ('Science', 'Force and motion'), ('Science', 'Basic electricity'),
            ('English', 'Grammar'), ('English', 'Subject-verb agreement'),
        }
        assert db.execute('SELECT COUNT(DISTINCT teacher_id) FROM classes').fetchone()[0] == 1
        rosters = dict(db.execute("""
            SELECT classes.topic, count(students.id)
            FROM classes LEFT JOIN students ON students.class_id = classes.id
            GROUP BY classes.id
        """))
        assert rosters == {
            'Fractions': 40, 'Basic algebra': 40, 'Force and motion': 40,
            'Basic electricity': 40, 'Grammar': 40, 'Subject-verb agreement': 40,
        }
        assert db.execute("SELECT count(*) FROM questions WHERE subject='Mathematics' AND topic='Fractions'").fetchone()[0] == 5
        new_student_rows = db.execute("""
            SELECT students.student_code, questions.question_text, questions.correct_answer,
                   submissions.answer, submissions.explanation
            FROM submissions
            JOIN students ON submissions.student_id = students.id
            JOIN questions ON submissions.question_id = questions.id
            JOIN classes ON classes.id = students.class_id
            WHERE classes.topic='Fractions'
              AND students.student_code BETWEEN 'DEMO-04' AND 'DEMO-40'
        """).fetchall()
        assert len(new_student_rows) == 37 * 5
        diagnosed_students = {}
        student_patterns = {}
        provider = RuleBasedDiagnosisProvider()
        for student_code, question, correct_answer, answer, explanation in new_student_rows:
            diagnosis = provider.diagnose(question=question, correct_answer=correct_answer,
                answer=answer, explanation=explanation)
            if diagnosis.misconception_code in {'M01', 'M02', 'M03', 'M04', 'M05'}:
                diagnosed_students.setdefault(diagnosis.misconception_code, set()).add(student_code)
                student_patterns.setdefault(student_code, set()).add(diagnosis.misconception_code)
        assert {code: len(students) for code, students in diagnosed_students.items()} == {
            'M01': 8, 'M02': 8, 'M03': 7, 'M04': 7, 'M05': 7,
        }
        assert set(student_patterns) == {f'DEMO-{number:02d}' for number in range(4, 41)}
        assert all(len(patterns) == 1 for patterns in student_patterns.values())
        assert db.execute("SELECT count(*) FROM submissions JOIN students ON submissions.student_id = students.id JOIN classes ON classes.id=students.class_id WHERE classes.topic='Fractions' AND students.student_code BETWEEN 'DEMO-04' AND 'DEMO-40'").fetchone()[0] == 185
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    # Re-running may not erase the first rehearsal.
    assert prepare(target).returncode != 0


def test_demo_refuses_existing_directory_even_if_class_name_matches(tmp_path):
    path = tmp_path / 'fractions.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE classes (class_name TEXT)')
        db.execute("INSERT INTO classes VALUES ('Synthetic Fractions demonstration')")
    before = path.read_bytes()
    assert prepare(tmp_path).returncode != 0
    assert path.read_bytes() == before


def test_restore_other_classes_on_existing_demo_preserves_saved_answers(tmp_path):
    target = tmp_path / 'existing-run'
    assert prepare(target).returncode == 0
    with sqlite3.connect(target / 'fractions.sqlite') as db:
        before = db.execute("SELECT students.student_code, submissions.answer FROM submissions JOIN students ON submissions.student_id = students.id WHERE students.student_code LIKE 'DEMO-%' ORDER BY students.student_code").fetchall()
    cmd = [sys.executable, '-m', 'scripts.run_map_demo', '--add-classes', str(target)]
    for _ in range(2):
        result = subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    with sqlite3.connect(target / 'fractions.sqlite') as db:
        after = db.execute("SELECT students.student_code, submissions.answer FROM submissions JOIN students ON submissions.student_id = students.id WHERE students.student_code LIKE 'DEMO-%' ORDER BY students.student_code").fetchall()
        assert before == after
        assert db.execute('SELECT count(*) FROM classes').fetchone()[0] == 6
        assert set(db.execute("SELECT classes.topic, count(students.id) FROM classes LEFT JOIN students ON students.class_id=classes.id GROUP BY classes.id")) == {
            ('Fractions', 40), ('Basic algebra', 40), ('Force and motion', 40),
            ('Basic electricity', 40), ('Grammar', 40), ('Subject-verb agreement', 40),
        }


def test_restore_classes_refuses_unmarked_database(tmp_path):
    with sqlite3.connect(tmp_path / 'fractions.sqlite') as db:
        db.execute('CREATE TABLE sentinel (value TEXT)')
        db.execute("INSERT INTO sentinel VALUES ('preserve')")
    cmd = [sys.executable, '-m', 'scripts.run_map_demo', '--add-classes', str(tmp_path)]
    assert subprocess.run(cmd, cwd=BACKEND, capture_output=True).returncode != 0
    with sqlite3.connect(tmp_path / 'fractions.sqlite') as db:
        assert db.execute('SELECT value FROM sentinel').fetchone()[0] == 'preserve'
