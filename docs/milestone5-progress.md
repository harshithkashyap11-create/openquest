# Milestone 5 Progress

## Status

Core teacher/student demo integration is implemented. Backend and frontend verification has passed for the checks listed below; browser-driven UI, accessibility-tool, and responsive-device checks remain untested. This is a local demo, not production authentication.

## Discovery Report

### Stack and existing project

- Active repository: `openpost/`. The separate `openquest` scaffold is not the runnable app.
- Frontend: React 19, Vite 8, JavaScript/JSX, React Router 7, Axios, plain CSS, Lucide icons, and Recharts. The existing Vite setup and CSS approach were retained.
- Frontend translations were flat JSON dictionaries for English, Hindi, and Telugu, using a local React provider. The provider persists language in `localStorage`; no external translation service or font CDN is used.
- Frontend pages existed as a Vite shell; the runnable app had no frontend test runner, PWA manifest, or service worker. Page-level routes are lazy-loaded.
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite/PostgreSQL. Existing health, diagnosis, group review, intervention, reassessment, and progress services were reused.
- The tracked `docs/` directory had no dedicated approved Milestone 5 architecture-plan document. Existing backend contracts and repository README were treated as the source of truth.
- The runnable app's source tree was inspected before the approved implementation. No Git metadata is present in this workspace, so a repository diff could not be used.

### API inventory discovered from live OpenAPI

| Method | Path | Purpose / response |
|---|---|---|
| GET | `/health` | Liveness status. |
| GET | `/health/ready` | Database readiness status. |
| GET | `/api/demo/classes` | Class ID, class name, subject, student count. |
| GET | `/api/demo/classes/{class_id}/students` | Demo student IDs and codes only; added for code selection. |
| POST | `/api/demo/students/resolve` | Resolves a class ID + student code to demo student identity. |
| GET | `/api/classes/{class_id}/assessment` | Fractions questions without answer keys; requires matching `X-Student-ID`. |
| POST | `/api/students/{student_id}/assessment-submissions` | Saves one attempt of answers and explanations; matching `X-Student-ID` required. |
| GET | `/api/classes/{class_id}/assessment-summary` | Student submission/diagnosis counts and assessment totals. |
| POST | `/api/classes/{class_id}/diagnose` | Processes a bounded batch of pending submissions; optional `limit`. |
| GET | `/api/classes/{class_id}/diagnoses` | Diagnosis rows; supports code, follow-up, student, limit, and offset filters. |
| GET | `/api/classes/{class_id}/diagnoses/summary` | Counts by misconception code and follow-up count. |
| GET | `/api/classes/{class_id}/groups` | Proposed/reviewed groups with member IDs and codes. |
| POST | `/api/classes/{class_id}/groups/generate` | Generates groups from eligible diagnoses. |
| PATCH | `/api/groups/{group_id}/review` | Approves or rejects a group via `{ "status": ... }`. |
| POST | `/api/groups/{group_id}/interventions/generate` | Generates an intervention and creates assignments for group members; includes provider/provenance. |
| GET | `/api/classes/{class_id}/intervention-assignments` | Teacher-facing assignment statuses and reassessment results. |
| GET | `/api/students/{student_id}/interventions` | Student's assignments without practice answer keys; matching `X-Student-ID` required. |
| GET | `/api/intervention-assignments/{assignment_id}` | Owned assignment details; matching `X-Student-ID` required. |
| POST | `/api/intervention-assignments/{assignment_id}/submit` | Backend grades practice answers; matching `X-Student-ID` required. |
| POST | `/api/intervention-assignments/{assignment_id}/complete` | Completes assignment and creates/returns reassessment; matching `X-Student-ID` required. |
| POST | `/api/intervention-assignments/{assignment_id}/reassessment` | Gets or creates the assignment's reassessment; matching `X-Student-ID` required. |
| GET | `/api/reassessments/{reassessment_id}` | Owned reassessment result; matching `X-Student-ID` required. |
| POST | `/api/reassessments/{reassessment_id}/submit` | Backend evaluates reassessment answers; matching `X-Student-ID` required. |
| GET | `/api/students/{student_id}/progress` | Own progress, observed accuracy, sample sizes; matching `X-Student-ID` required. |
| GET | `/api/classes/{class_id}/progress` | Class aggregate progress and backend support queue. |

Development and preview use Vite's `/api` proxy; no broad CORS policy was added. Direct cross-origin deployments need their own allowed-origin configuration.

### UI-to-API mapping and gaps

| UI need | Endpoint | Request / response used | Notes |
|---|---|---|---|
| Class roster and class selection | `GET /api/demo/classes` | No body; class summaries. | Real backend data. |
| Student code selection and validation | `GET /api/demo/classes/{id}/students`, `POST /api/demo/students/resolve` | Roster returns code/ID; resolution takes class ID and code. | Added the read-only roster route (GAP-A). |
| Assessment question fetch/submission | `GET /api/classes/{id}/assessment`, `POST /api/students/{id}/assessment-submissions` | Question IDs/text; submitted answer + explanation array. | Student header enforced; question payload omits answer keys. |
| Diagnosis status/distribution | `GET /api/classes/{id}/assessment-summary`, `GET /api/classes/{id}/diagnoses`, `GET /api/classes/{id}/diagnoses/summary`, `POST /api/classes/{id}/diagnose` | Status counts, diagnosis rows, summary counts. | Insights use backend status, confidence, evidence, and provider. |
| Group review | `GET /api/classes/{id}/groups`, `POST /api/classes/{id}/groups/generate`, `PATCH /api/groups/{id}/review` | Group list, generated groups, review status. | Group review is part of the combined teacher interventions page. |
| Generate and deliver intervention | `POST /api/groups/{id}/interventions/generate` | Targeted activity, provider, generated assignments. | Existing API assigns on generation; separate preview/assign action is unavailable. |
| Student activity and practice | Student intervention list/detail and `/submit`/`complete` routes | Owned assignment and practice results. | All student requests carry `X-Student-ID`; answer keys are omitted from student responses. |
| Reassessment and scoring | Assignment reassessment and reassessment submit/get routes | Fresh questions and backend score/results. | No separate global list endpoint; available from completed assignments. |
| Personal/class progress | `GET /api/students/{id}/progress`, `GET /api/classes/{id}/progress` | Accuracy, sample sizes, assignment counts, support queue. | Class endpoint is aggregate-only; no per-student class-score table or recent activity feed exists (GAP-C). |
| Health / language | `GET /api/demo/classes`; client dictionaries | Class list used as read-only availability probe; language stored locally. | No server-side language preference endpoint. |

### Known gaps and classifications

- **GAP-A implemented:** no class-scoped demo roster endpoint existed. Added a minimal read-only route with a response schema, service function, and test.
- **GAP-C / backend contract limitation:** intervention generation creates and assigns to group members in one call. The interface labels this as generate-and-assign and displays the returned provider and activity; it cannot offer a separate preview/confirmation step without an additive backend workflow.
- **GAP-C:** class progress exposes aggregates/support flags, not each student's before/after scores or completed activities. The class page displays only returned aggregates and the backend support queue.
- **GAP-A not implemented:** there is no general recent-activity feed endpoint, so the dashboard does not invent activity rows.
- **GAP-A not implemented:** no dedicated class-level list of individual progress rows is exposed.
- No production authentication, external translation, or hidden/demo fixture data was added.

### Files planned and implemented

Created: frontend provider/hook separation files, `ClassProgress.jsx`, `NotFound.jsx`, `frontend/.env.example`, `scripts/check-i18n.mjs`, `scripts/smoke_api.py`, and this report/progress documentation.

Modified: active frontend routing, shell, API client/wrappers, data hook, login/activity pages, translation dictionaries, CSS, Vite configuration, and project README; backend demo schemas/service/router, backend API tests, and generated `backend/schema.sql`.

## Progress Log

| Date/time (UTC) | Work or check | Outcome |
|---|---|---|
| 2026-11-01 13:22–13:23 | Initial verification commands were accidentally run from the workspace parent. | Corrected to run commands from `openpost/frontend` and `openpost/backend`; no files were changed by the failed commands. |
| 2026-11-01 13:22–13:24 | Frontend lint/build and backend suite from project directories. | Frontend lint/build initially passed with Fast Refresh warnings; backend reported 56 passed, 1 skipped. |
| 2026-11-01 13:24–13:26 | Added class roster, backend availability status, class progress page, provider display, route/title/focus details, API base normalization, and translation keys. | Implemented using existing Vite/React/API patterns; no dependency added. |
| 2026-11-01 13:26 | Roster test-first check. | New test returned 404 before route implementation, then passed after adding the route. |
| 2026-11-01 13:26–13:28 | Frontend lint/build/i18n check, backend suite, SQLite migrations, and API smoke tests. | Lint clean; production build succeeded; English/Hindi/Telugu dictionaries match; backend suite 56 passed, 1 skipped; migration to `0004_submission_attempts` succeeded. |
| 2026-11-01 13:27–13:28 | End-to-end API flow against a disposable SQLite demo database with mock AI. | Diagnosed 40 submissions; generated 4 proposed groups; approved a regular group; generated 1 template intervention and 8 assignments; submitted practice, completed one assignment, generated 3 reassessment questions, submitted answers, and observed class progress update. |
| 2026-11-01 13:28–13:29 | Production preview and API proxy check. | Port 4173 was already occupied, so preview ran on 4187; root and deep route returned 200 and `/api/demo/classes` proxied successfully. No process on 4173 was changed. |
| 2026-11-01 13:29 | Regenerated offline PostgreSQL `backend/schema.sql` from Alembic through revision `0004_submission_attempts`. | Export now includes the `attempt_no` column and its constraints. |
| 2026-11-01 13:30 | Final verification after dashboard, diagnosis-status, and translation updates. | Frontend lint/build/i18n, backend tests, script syntax checks, centralized API check, and preview root/deep-route/API proxy all passed. |

## Verification Status

- `cd openpost/frontend && npm run lint`: passed with no warnings on the final source.
- `cd openpost/frontend && npm run build`: passed. Main JS chunk was 372.32 kB (117.58 kB gzip); ClassInsights route chunk was 363.07 kB (105.04 kB gzip).
- `cd openpost/frontend && npm run i18n:check`: passed; all 217 keys match in English, Hindi, and Telugu.
- `cd openpost/backend && python -m pytest -q`: 56 passed, 1 skipped. Two third-party deprecation warnings remain.
- `cd openpost/backend && DATABASE_URL=sqlite+pysqlite:///... python -m alembic upgrade head`: passed on a disposable SQLite DB through migration 0004.
- `python scripts/smoke_api.py` against the current source on port 8001: all eight health, class, roster, assessment-summary, diagnosis-summary, groups, progress, and assignment-report checks returned 200.
- Preview check on port 4187: root route, `/teacher/progress` deep link, and `/api/demo/classes` proxy returned 200; latest build title is `ClassPulse AI`.
- `python -m py_compile scripts/smoke_api.py` and `node --check scripts/check-i18n.mjs`: passed. Frontend source check found no direct `fetch()` calls or hardcoded backend host.
- Browser UI flows, screen reader, axe, responsive widths, failure-state visuals, and full console/network audit: **NOT TESTED**.
