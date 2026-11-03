# ClassPulse AI

ClassPulse AI is a classroom intelligence platform MVP for Mathematics (Fractions and Basic algebra), Science (Force and motion and Basic electricity), and English (Grammar and Subject-verb agreement). The FastAPI backend provides SQLite/PostgreSQL persistence, Alembic migrations, labeled synthetic demo data, subject-specific diagnosis, teacher-reviewed learning groups, targeted interventions, adaptive reassessments, and observed progress reporting. The React/Vite frontend provides teacher and student demo flows over the FastAPI API.

The Node/Express prototype is archived under `legacy/node-backend/`; the FastAPI service is the active backend. No multi-agent framework or production authentication is used.

## Prerequisites

- Docker Engine with Docker Compose v2, or Python 3.12+ and PostgreSQL 16+
- For local Python development: `pip`

## Configure the environment

From `openpost/`, copy `.env.example` to `.env` if you do not already have a local `.env`. The example values are for local development only; replace them for any shared environment. Do not commit `.env`.

The SQLAlchemy URL must use the Psycopg 3 dialect:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

URL-encode special characters in credentials.

## Run with Docker Compose

```bash
docker compose --env-file .env.example up --build -d
docker compose --env-file .env.example ps
docker compose --env-file .env.example exec api alembic upgrade head
```

Compose starts PostgreSQL with a persistent named volume, waits for its health check before starting the API, and exposes the local API at `http://localhost:8000`. To use your copied `.env` instead, omit `--env-file .env.example`.

The health endpoints are:

- `GET http://localhost:8000/health` — application liveness
- `GET http://localhost:8000/health/ready` — PostgreSQL-backed readiness
- `GET http://localhost:8000/docs` — interactive OpenAPI documentation

## Diagnose submissions and propose groups

Diagnosis uses `AI_PROVIDER=mock` by default, so local demos require no API key or network access. The deterministic mock provider retains the fractions heuristics; for the other topics it requests a diagnostic follow-up rather than fabricating a misconception. It returns `"provider": "mock"` and never reads `data/ground_truth.json`.

To use OpenRouter, create an API key from your OpenRouter account's **Keys** page. Put it only in the repository-root `.env` as `OPENROUTER_API_KEY=...`; never put it in a frontend environment file. Set `AI_PROVIDER=openrouter` and configure `OPENROUTER_MODEL` using a model ID in `provider/model` format from the OpenRouter model catalog. `OPENROUTER_BASE_URL` defaults to `https://openrouter.ai/api/v1`. The `.env` file is ignored by Git. There is no implicit switch to mock mode when a real request fails; diagnosis returns an error, while intervention generation may explicitly report its predefined template fallback.

Switch back to offline mode by setting `AI_PROVIDER=mock`. OpenRouter requests have a configurable `OPENROUTER_TIMEOUT_SECONDS` timeout. Diagnosis batches process at most 20 submissions and have a bounded overall timeout.

Run pending diagnosis batches and view results:

```text
POST /api/classes/{class_id}/diagnose
GET  /api/classes/{class_id}/diagnoses
GET  /api/classes/{class_id}/diagnoses/summary
```

Generate and review groups:

```text
POST  /api/classes/{class_id}/groups/generate
GET   /api/classes/{class_id}/groups
PATCH /api/groups/{group_id}/review
```

Generate and deliver interventions after a teacher approves a group:

```text
POST /api/groups/{group_id}/interventions/generate
GET  /api/students/{student_id}/interventions
GET  /api/intervention-assignments/{assignment_id}
POST /api/intervention-assignments/{assignment_id}/submit
POST /api/intervention-assignments/{assignment_id}/complete
POST /api/intervention-assignments/{assignment_id}/reassessment
POST /api/reassessments/{reassessment_id}/submit
GET  /api/classes/{class_id}/progress
```

M01–M05 use verified, misconception-specific templates; M06 is reserved for a
diagnostic follow-up rather than routine remediation. OpenRouter can personalize
explanations and teaching language, but never generates or grades answer keys.
When OpenRouter personalization is unavailable, the response identifies the
saved provider as `template` and includes a generation note. Student endpoints require an `X-Student-ID` header matching the
requested student. This is a local-demo identity check, not production
authentication. Student activity and reassessment responses omit correct
answers; submissions are graded by the backend.

Diagnoses preserve an exact supporting quote from the submitted answer or explanation. Low-confidence and M06 results are placed in the follow-up/review queue. Only supported misconception diagnoses at confidence 0.75 or higher can be proposed as groups; groups need at least two distinct students and remain subject to teacher approval.

After submissions have diagnoses, compare stored predictions against the offline synthetic labels:

```bash
cd backend
python -m scripts.evaluate_diagnoses
```

The evaluator is the only runtime component that reads `data/ground_truth.json`.

Check migration state with:

```bash
docker compose --env-file .env.example exec api alembic current
```

`backend/schema.sql` is a generated offline SQL export, not an independent schema source. Regenerate it from Alembic after migration changes:

```bash
docker compose --env-file .env.example run --rm api alembic upgrade head --sql > backend/schema.sql
```

## Run locally without the API container

Start PostgreSQL with Compose, then install and run the backend from a Python environment:

```bash
docker compose --env-file .env.example up -d db
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd backend
DATABASE_URL='postgresql+psycopg://classpulse:change-me-before-deploy@localhost:5433/classpulse' alembic upgrade head
DATABASE_URL='postgresql+psycopg://classpulse:change-me-before-deploy@localhost:5433/classpulse' uvicorn app.main:app --reload
```

Set `DATABASE_URL` from your environment rather than using the sample values when your local database uses different credentials.

For an isolated SQLite demo, run these commands from `openpost/backend/`:

```bash
python -m alembic upgrade head
python -m scripts.import_synthetic_dataset --include-multisubject
python -m uvicorn app.main:app --reload
```

These commands use the repository-root `.env`; the default SQLite database is
relative to the backend working directory. For taxonomy-based diagnosis across
all subjects, configure `AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, and
`OPENROUTER_MODEL` in the root `.env`. Mock mode remains suitable for offline
fractions demonstrations and intentionally requests follow-up on other topics
rather than inventing their diagnoses.

This keeps the standard PostgreSQL setup unchanged while allowing the complete
intervention workflow to run against a local SQLite file.

## Run the frontend demo

Start the backend using the SQLite or PostgreSQL instructions above, then in a
second terminal:

```bash
cd openpost/frontend
npm install
CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8000 npm run dev
```

Open the Vite URL (usually `http://localhost:5173`). Choose a teacher and class
to review assessment status, diagnoses, learning groups, interventions, and
progress. Choose student access and enter a student code from the selected
class to submit an assessment, complete assigned activities, and view personal
progress. The frontend reads optional configuration from
`frontend/.env` (copy `frontend/.env.example`): `VITE_API_BASE_URL` accepts a
backend origin with or without the `/api` suffix, while
`CLASS_PULSE_BACKEND_URL` controls the Vite development proxy. Without an API
URL override, `/api` is proxied to `http://127.0.0.1:8000`.

Useful frontend checks, run from `openpost/frontend/`:

```bash
npm run lint
npm run build
npm run i18n:check
```

The read-only API smoke script can be run from `openpost/` after starting the
backend:

```bash
python scripts/smoke_api.py
```

For a different backend origin, set `CLASS_PULSE_API_URL` before running the
smoke script.

Role selection and student-code entry are demonstration access controls, not
secure authentication. Do not expose this demo over an untrusted network.

To verify a real OpenRouter connection without printing the key or response,
first set `AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL`
in the repository-root `.env`. Then run from `openpost/backend/`:

```bash
python - <<'PY'
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path("../.env").resolve())
key = os.environ.get("OPENROUTER_API_KEY", "")
model = os.environ.get("OPENROUTER_MODEL", "")
base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
if not key or not model:
    raise SystemExit("Set OPENROUTER_API_KEY and OPENROUTER_MODEL in ../.env first.")

try:
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "max_tokens": 8,
        },
        timeout=30,
    )
except httpx.HTTPError:
    raise SystemExit("OpenRouter request failed (connection or timeout).")
if response.is_error:
    raise SystemExit(f"OpenRouter returned HTTP {response.status_code}.")
print("OpenRouter request succeeded (HTTP 200); response and key were not printed.")
PY
```

The demo entry screen first filters available classes by subject and topic using
`GET /api/demo/classes`, then loads student codes
from `GET /api/demo/classes/{class_id}/students`, and validates typed codes via
`POST /api/demo/students/resolve`. The roster endpoint returns only the
synthetic student ID and code; it does not expose submissions or answer data.
The fractions class has student codes `S001`–`S040`; the other topic classes
use codes prefixed by `ALG`, `FM`, `EL`, `GR`, and `SV`. These are demo
identifiers, not credentials.

## Import the synthetic data

After migrations are applied:

```bash
docker compose --env-file .env.example exec api python -m scripts.import_synthetic_dataset --include-multisubject
```

The importer reads `data/synthetic_responses.csv`; with `--include-multisubject`, it also imports `data/multi_subject_synthetic_responses.csv` and creates a separate demo class for each of the five additional topics. All rows in both files are deterministic synthetic examples, not real learners or precomputed diagnosis labels. The importer inserts catalog questions and student submissions with deterministic UUIDs and idempotent database constraints. It never reads `data/ground_truth.json`; that file is reserved for offline model evaluation.

The verified starter answer keys and topic metadata are in `backend/app/question_catalog.py`; subject-specific misconception categories are in `backend/app/subject_taxonomy.py` and `docs/misconception_taxonomy.md`. Educators should review this engineering-authored demo content before classroom use.

## Tests

Run unit/API/model/import tests in the backend directory:

```bash
cd backend
python -m pytest -q
```

The SQLite-backed unit tests do not require a running database. PostgreSQL integration tests require a **disposable** database with the Alembic migration applied. With Compose running, create and migrate one:

```bash
docker compose -f ../docker-compose.yml --env-file ../.env.example exec -T db createdb -U classpulse -O classpulse classpulse_test
docker compose -f ../docker-compose.yml --env-file ../.env.example exec -e DATABASE_URL='postgresql+psycopg://classpulse:change-me-before-deploy@db:5432/classpulse_test' api alembic upgrade head
docker compose -f ../docker-compose.yml --env-file ../.env.example exec -e CLASS_PULSE_TEST_DATABASE_URL='postgresql+psycopg://classpulse:change-me-before-deploy@db:5432/classpulse_test' api python -m pytest -q
```

The integration test imports the synthetic dataset into that test database and verifies a rerun is idempotent. Do not point it at production or a database containing non-test data.

## Troubleshooting

- **Driver/module error:** Check that `DATABASE_URL` starts with `postgresql+psycopg://`; plain `postgresql://` selects a different driver.
- **Connection refused:** Confirm PostgreSQL is healthy with `docker compose ps`; allow a few seconds for the health check.
- **Authentication/database error:** Ensure `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` match the URL. If changing credentials after the named volume has already been initialized, update/reset the local development volume only when its data is disposable.
- **Missing tables:** Run `alembic upgrade head`; the application intentionally does not create tables at startup.
- **Port already allocated:** Change the host-side port mapping in `docker-compose.yml` and use the new port in the host `DATABASE_URL`.

All learner records in the included CSV are synthetic. Authentication, production privacy controls, and classroom-ready educational content review are outside this backend-foundation milestone.

## Teacher quizzes, student reflection, and live reports

The **Quizzes** navigation now opens teacher authoring/CSV import and student quiz access. Teachers save and review drafts before publishing; students submit answers, discuss missed questions with the learning sidebar, and attempt optional teacher-approved repair challenges. Teacher reports refresh while visible, show answer distributions and supported error themes, and allow interpretation flags and review of a next-lesson suggestion. The existing teacher copilot also receives recent quiz summaries.

Apply the new migration with `python3 -m alembic upgrade head` from `backend` before starting the updated API. Rebuild the API image first if using Docker. API keys remain server-side; `AI_PROVIDER=mock` provides labeled template feedback for a network-independent demonstration. Live provider failures preserve submitted grades and expose a retry state.

See [the quiz implementation and demo guide](docs/quiz_learning_loop.md) for startup, CSV columns, API contracts, architecture, verification, and limitations. Browser acceptance tests run with `npm run test:e2e` from `frontend` and use their own disposable SQLite/mock API.

### Use Google Gemini directly

Set `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, and `GEMINI_MODEL` in the ignored repository-root `.env`. The default model is `gemini-3.5-flash-lite`; choose another available text-generation model explicitly if needed. Gemini uses the native Google API with JSON output. The student reflection sidebar, teacher copilot, lesson suggestions, and legacy diagnosis/intervention personalization share this provider choice. Restart the backend after updating the configuration. Docker Compose also forwards these settings.

The key stays in backend request headers. `GEMINI_TIMEOUT_SECONDS` defaults to 45 seconds, and sidebar browser requests allow 60 seconds. Unavailable or rate-limited generation is reported clearly; template responses are labeled and do not count as verified live AI output. No Gemini key belongs in a frontend environment file.

## ClassPulse Atelier interface upgrade

The existing teacher, student, quiz and Copilot workflows now share botanical
teal design tokens, responsive navigation, accessible evidence/member dialogs,
answer-preserving question navigation and persistent Auto/Lite/Full effects.
No new runtime dependencies are required. Reduced motion always overrides Full.

See [the engineering report](docs/upgrade-progress.md) for measured results,
known limitations and the full verification checklist, and
[the three-minute demonstration guide](docs/three-minute-demo.md) for preparation
against real persisted demo records. Live provider availability must be checked
separately; the isolated browser suite uses the labeled mock/template provider.

To test the production frontend against a fresh disposable backend:

```bash
cd frontend
npm run build
CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e
```
