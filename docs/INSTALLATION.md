# Verified local installation and startup

Run the commands below from the OpenQuest repository root unless a command changes directory.
Executed runtime: Python 3.14.7, Node 22.23.1, npm 10.9.8. The backend requirements
remain compatible declarations rather than a fully pinned lockfile; other Python
versions and a clean dependency installation were not re-tested in this upgrade.
No new runtime dependency is required for the learning additions.

If dependencies are absent, create a virtual environment and install the existing
requirements. These are installation instructions, not a claim that a fresh install
was executed during verification:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd ../frontend
npm ci
```

Do not overwrite an existing `.env`. `.env.example` documents the provider options.
DATABASE_URL is required. The local environment already selects native Gemini;
OpenRouter remains supported through AI_PROVIDER=openrouter, OPENROUTER_API_KEY,
OPENROUTER_MODEL and its existing URL/timeout options. Native Gemini uses
GEMINI_API_KEY/GEMINI_MODEL. Keys remain server-side and must not use VITE_ variables.
Mock mode requires no key and never claims live inference.

Initialize the dedicated synthetic demo (does not use or erase the existing app DB):

```bash
cd backend
python -m scripts.prepare_demo --dry-run
python -m scripts.prepare_demo --with-accounts
```

This applies reviewed migration 0007 to `.classpulse-demo/classpulse-demo.sqlite`,
marks it as a synthetic database, seeds three subject contexts and six synthetic
learners, and optionally creates private accounts. Generated passwords are in
`.classpulse-demo/credentials.json`, mode 0600; they are not printed. Initialization
is idempotent. It refuses an existing unmarked database and has no reset command.

Run the local synthetic role-selection demo in one terminal:

```bash
cd backend
DATABASE_URL='sqlite:///../.classpulse-demo/classpulse-demo.sqlite' APP_ENV=development AUTH_MODE=demo AI_PROVIDER=mock python -m uvicorn app.main:app --host 127.0.0.1 --port 8018
```

To use the configured live provider, omit AI_PROVIDER=mock; do not edit the private
.env just to switch the demo command. To demonstrate verified accounts, replace
AUTH_MODE=demo with AUTH_MODE=required and use the privately generated account.
Teacher account: `demo-teacher`; student accounts: `demo-student-mathematics`,
`demo-student-science`, `demo-student-english`. A non-development deployment must
use required mode and HTTPS because its cookies are Secure.

Run the frontend in another terminal. Production preview is required for offline
shell testing; development mode intentionally does not register the service worker.

```bash
cd frontend
npm run build
CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8018 npm run preview -- --host 127.0.0.1 --port 5188 --strictPort
```

Open `http://127.0.0.1:5188`. For ordinary development:

```bash
CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8018 npm run dev -- --host 127.0.0.1
```

Health and opt-in live verification (only synthetic embedded prompts are sent):

```bash
cd backend
python -m scripts.check_health --base-url http://127.0.0.1:8018
python -m scripts.probe_ai --live --output /tmp/classpulse-provider-smoke.json
python -m scripts.verify_live_lessons --live --output /tmp/classpulse-live-lessons.json
python -m scripts.verify_live_tutor --live --output /tmp/classpulse-live-tutor.json
```

For an existing deployment, first back up and inspect its target DATABASE_URL,
then run `python -m alembic upgrade head` from backend with the correct environment.
No migration was applied to the user's original local database by this upgrade.
0007 is additive. Its downgrade drops only the new learning/auth/lesson tables and
therefore destroys their new history; use downgrade only on disposable data or
with a verified backup. Legacy row preservation and SQLite upgrade/downgrade were
tested. PostgreSQL execution of the new revision remains NOT TESTED.

Verification commands:

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd ../frontend
npm run build
npm run lint
npm run i18n:check
CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e
```

Browser tests start their own disposable SQLite/mock API on 8012 and frontend on
5181. They do not require or alter the running demonstration database. Bare
`pytest` had an environment-specific import-path failure; module invocation works.


## Fresh map demo (2026-11-05)

For the new assessment/map journey, prefer `python -m scripts.run_map_demo` from
backend after installing the existing requirements. It builds the frontend and
starts localhost ports 8019/5189 against a fresh private SQLite file. No new
package, migration, cloud service or key is required. See DEMO_GUIDE.md for the
synthetic record labels, actual buttons and recovery. Existing demo initialization
still works; it is a different, fixture-backed walkthrough. Neither command is a
destructive reset. Run the new command again to create another independent run.
