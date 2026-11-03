"""Run a disposable SQLite/mock API for browser acceptance tests only."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

backend = Path(__file__).resolve().parents[1] / "backend"
with tempfile.TemporaryDirectory(prefix="classpulse-browser-") as temporary:
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{temporary}/test.sqlite",
        "AI_PROVIDER": "mock",
        "OPENROUTER_API_KEY": "",
        "GEMINI_API_KEY": "",
        "OPENROUTER_MODEL": "",
    }
    for arguments in [
        ["-m", "alembic", "upgrade", "head"],
        ["-m", "scripts.import_synthetic_dataset", "--include-multisubject"],
    ]:
        subprocess.run([sys.executable, *arguments], cwd=backend, env=env, check=True)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8012",
        ],
        cwd=backend,
        env=env,
    )

    def stop(_signal, _frame):
        process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
