import os
from pathlib import Path
import sqlite3
import subprocess
import sys

BACKEND=Path(__file__).resolve().parents[1]

def run(directory,*extra):
    return subprocess.run([sys.executable,'-m','scripts.prepare_demo','--directory',str(directory),*extra],cwd=BACKEND,
        env={**os.environ,'APP_ENV':'test','AUTH_MODE':'demo','AI_PROVIDER':'mock'},capture_output=True,text=True)


def test_demo_initialization_is_idempotent_and_dry_run_writes_nothing(tmp_path):
    target=tmp_path/'dedicated'
    assert run(target,'--dry-run').returncode==0
    assert not target.exists()
    assert run(target).returncode==0
    assert run(target).returncode==0
    with sqlite3.connect(target/'classpulse-demo.sqlite') as db:
        assert db.execute('SELECT COUNT(*) FROM students').fetchone()[0]==6
        assert db.execute('SELECT COUNT(*) FROM diagnoses').fetchone()[0]==6
        assert db.execute("SELECT COUNT(*) FROM learning_events WHERE kind='diagnosis'").fetchone()[0]==6
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_demo_refuses_an_existing_unmarked_database(tmp_path):
    with sqlite3.connect(tmp_path/'classpulse-demo.sqlite') as db:
        db.execute('CREATE TABLE sentinel (value TEXT)')
        db.execute("INSERT INTO sentinel VALUES ('preserve')")
    result=run(tmp_path)
    assert result.returncode!=0
    assert 'not positively marked' in result.stderr
    with sqlite3.connect(tmp_path/'classpulse-demo.sqlite') as db:
        assert db.execute('SELECT value FROM sentinel').fetchone()[0]=='preserve'
