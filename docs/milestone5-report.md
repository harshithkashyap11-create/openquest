# ClassPulse AI — Milestone 5 Report

## 8.1 Summary

The runnable `openpost` app now has a responsive React/Vite teacher/student demo connected to the active FastAPI backend, including demo roster selection, assessment submission, diagnosis/group review, targeted intervention assignment, reassessment, and observed progress pages. The backend/frontend builds, backend suite, i18n parity check, disposable-database API smoke flow, migration, and production preview routes passed. Browser-driven interaction, screen-reader/accessibility-tool, and device-width checks were not run, so the milestone is not claimed as fully browser-verified.

## 8.2 Files created and modified

**Created**

- Backend: `backend/app/routes/classroom.py` and `backend/app/services/classroom_service.py` add demo discovery, assessment, and class/student reporting logic.
- Backend: `backend/app/schemas/classroom.py` and `backend/app/schemas/teacher_reports.py` define response/request contracts.
- Backend: `backend/alembic/versions/0004_submission_attempts.py` adds attempt-aware assessment submissions.
- Backend: `backend/tests/test_milestone5_api.py` covers the additive Milestone 5 API behavior.
- Frontend: `frontend/src/components/{AppShell,LanguageSelector,MetricCard,PageHeader,PageStates}.jsx`, `frontend/src/context/{DemoSessionContext,demoSessionContext,useDemoSession}.js`, `frontend/src/hooks/useAsyncData.js`, and `frontend/src/services/{api,classpulseApi}.js`.
- Frontend pages: `frontend/src/pages/{Assessment,ClassInsights,ClassProgress,Intervention,Login,NotFound,StudentDashboard,StudentProgress,TeacherDashboard}.jsx`.
- Frontend i18n: `frontend/src/i18n/{I18nProvider,i18nContext,useI18n}.js` and `frontend/.env.example`.
- Utilities/docs: `scripts/check-i18n.mjs`, `scripts/smoke_api.py`, `docs/milestone5-progress.md`, and this report.

**Modified**

- Backend: `backend/app/main.py` registers the classroom router; `backend/app/models/submission.py` and `backend/app/services/progress_service.py` support attempt-aware baselines and progress; `backend/app/routes/diagnoses.py` accepts a student filter; `backend/schema.sql` was regenerated through Alembic revision 0004.
- Frontend: `frontend/src/App.jsx`, `frontend/src/App.css`, `frontend/src/index.css`, `frontend/index.html`, `frontend/vite.config.js`, `frontend/package.json`, all three `frontend/src/i18n/{en,hi,te}.json` dictionaries, and the page/provider/hook files listed above.
- Documentation: `README.md` documents local demo setup, environment values, demo authentication limitations, student codes, smoke checks, and i18n checks.

## 8.3 Pages implemented

| Route | Page | Role | Status | Notes |
|---|---|---|---|---|
| `/login` | Demo entry | Teacher/student | Partial | Real class/student roster; typed code is checked by the backend. UI not manually browser-tested. |
| `/teacher/overview` | Teacher dashboard | Teacher | Partial | Backend-derived class, assessment, diagnosis, follow-up, and progress metrics; diagnosis action. |
| `/teacher/insights` | Class insights | Teacher | Partial | Submission status, diagnosis confidence/evidence/provider, misconception chart and student filter. |
| `/teacher/interventions#groups` | Group review | Teacher | Partial | Group generation, member codes, approval/rejection. Combined with interventions in one page. |
| `/teacher/interventions#assignments` | Interventions and assignment tracking | Teacher | Partial | Generation/provenance and assignment/reassessment table; generation auto-assigns via existing backend contract. |
| `/teacher/progress` | Class progress | Teacher | Partial | Aggregate scores/sample sizes, completion counts and backend support queue; no individual-score table API. |
| `/student/dashboard` | Student dashboard | Student | Partial | Assessment and assigned/completed activity links from backend data. |
| `/student/assessment` | Fractions assessment | Student | Partial | Answers and explanations submit to backend; no browser test performed. |
| `/student/interventions` | Assigned activities | Student | Partial | Lists only the current demo student's assigned interventions. |
| `/student/interventions/:assignmentId` | Activity and reassessment | Student | Partial | Practice is graded by backend; completion triggers reassessment. |
| `/student/progress` | Personal progress | Student | Partial | Backend scores, sample sizes, assignment counts, and non-causal comparison framing. |
| `*` | Not found | Both | Partial | Friendly not-found route; browser test not performed. |

## 8.4 API endpoints integrated

| Method | Path | Used by | Notes |
|---|---|---|---|
| GET | `/health` | Smoke script | Liveness. |
| GET | `/api/demo/classes` | Entry, backend status indicator | Read-only class list and API availability probe. |
| GET | `/api/demo/classes/{class_id}/students` | Entry | Added read-only roster API for code selection. |
| POST | `/api/demo/students/resolve` | Entry | Validates typed student code. |
| GET | `/api/classes/{class_id}/assessment` | Student dashboard/assessment | Answer key withheld; requires `X-Student-ID`. |
| POST | `/api/students/{student_id}/assessment-submissions` | Assessment | Stores answers and explanations; matching student header required. |
| GET | `/api/classes/{class_id}/assessment-summary` | Teacher dashboard/insights | Real assessment submission/diagnosis counts. |
| POST | `/api/classes/{class_id}/diagnose` | Teacher dashboard | Existing backend diagnosis action; processes bounded batches. |
| GET | `/api/classes/{class_id}/diagnoses` | Class insights | Paginated diagnosis rows and student filter. |
| GET | `/api/classes/{class_id}/diagnoses/summary` | Teacher dashboard/insights | Misconception and follow-up counts. |
| GET | `/api/classes/{class_id}/groups` | Teacher interventions | Lists actual group status and members. |
| POST | `/api/classes/{class_id}/groups/generate` | Teacher interventions | Generates group suggestions. |
| PATCH | `/api/groups/{group_id}/review` | Teacher interventions | Persists approve/reject. |
| POST | `/api/groups/{group_id}/interventions/generate` | Teacher interventions | Returns targeted activity/provider and creates member assignments. |
| GET | `/api/classes/{class_id}/intervention-assignments` | Teacher interventions | Assignment status and reassessment outcomes. |
| GET | `/api/students/{student_id}/interventions` | Student dashboard/activity list | Own assignments only; matching student header required. |
| GET | `/api/intervention-assignments/{assignment_id}` | Student activity | Ownership-checked activity detail. |
| POST | `/api/intervention-assignments/{assignment_id}/submit` | Student activity | Server grades practice answers. |
| POST | `/api/intervention-assignments/{assignment_id}/complete` | Student activity | Completes assignment and creates/returns reassessment. |
| POST | `/api/intervention-assignments/{assignment_id}/reassessment` | Student activity | Gets/creates reassessment. |
| POST | `/api/reassessments/{reassessment_id}/submit` | Student activity | Server evaluates objective responses. |
| GET | `/api/reassessments/{reassessment_id}` | Student activity | Ownership-checked results. |
| GET | `/api/students/{student_id}/progress` | Student progress | Own progress and sample sizes. |
| GET | `/api/classes/{class_id}/progress` | Teacher dashboard/class progress | Aggregate accuracy/completion and support queue. |

## 8.5 Missing or incomplete backend capabilities

- **Separate intervention preview and assignment:** the existing generation endpoint creates assignments immediately for group members. The interface labels the operation “Generate and assign” and displays the returned provider/activity. The smallest future change is a separate intervention-create endpoint and an explicit assignment endpoint.
- **Per-student class progress table:** class progress currently returns aggregate scores/completions and support flags, not each student's before/after scores/activity count. The class page uses only available aggregate data; a read-only class progress detail endpoint is needed for the requested sortable per-student comparison.
- **Recent activity feed:** no backend endpoint returns a unified recent activity stream, so the dashboard does not invent activity rows.
- **Reassessment discovery:** reassessments are reachable from completed assignments; there is no separate student reassessment-list endpoint or global reassessment navigation.
- **Diagnosis follow-up for M06:** M06 remains a diagnostic follow-up case rather than standard remediation. The UI displays the backend-provided follow-up question/status where available; no separate student diagnostic follow-up submission workflow was added.
- Demo student identity and teacher access remain intentionally non-secure; the `X-Student-ID` header is a local-demo ownership check only.

## 8.6 Commands to run

From `openpost/backend/`, create a local SQLite database, migrate, import the synthetic dataset, and start the API:

```bash
DATABASE_URL='sqlite+pysqlite:///./classpulse.db' python -m alembic upgrade head
DATABASE_URL='sqlite+pysqlite:///./classpulse.db' python -m scripts.import_synthetic_dataset
DATABASE_URL='sqlite+pysqlite:///./classpulse.db' AI_PROVIDER=mock python -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd openpost/frontend
npm install
cp .env.example .env
npm run dev
npm run lint
npm run build
npm run preview
npm run i18n:check
```

Read-only API smoke check from `openpost/`:

```bash
python scripts/smoke_api.py
# Optional: CLASS_PULSE_API_URL=http://127.0.0.1:8000 python scripts/smoke_api.py
```

Backend tests and migration command:

```bash
cd openpost/backend
python -m pytest -q
DATABASE_URL='sqlite+pysqlite:///./classpulse.db' python -m alembic upgrade head
```

The included demo class has codes `S001`–`S040`; these are synthetic identifiers, not credentials. The frontend defaults to Vite's `/api` proxy; `frontend/.env.example` documents optional `VITE_API_BASE_URL` and `CLASS_PULSE_BACKEND_URL`.

## 8.7 Test results

### Verification matrix

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | Frontend starts | NOT TESTED | Production preview served successfully; `npm run dev` was not manually opened in a browser. |
| 2 | Backend starts | PASS | Disposable SQLite-backed API responded on port 8001; `/health` returned 200. |
| 3 | API connectivity | PASS | Read-only smoke script passed all eight endpoint checks; preview `/api` proxy returned a class. |
| 4 | Teacher dashboard real data | NOT TESTED | Backend summary/progress endpoints returned seeded data; no browser comparison. |
| 5 | Student dashboard real data | NOT TESTED | Student APIs were exercised directly; no browser rendering check. |
| 6 | Assessment submission | PASS (API) / NOT TESTED (UI) | Backend tests cover attempt creation and preserved baseline; no browser submission. |
| 7 | Diagnosis results appear | PASS (API) / NOT TESTED (UI) | Disposable API diagnosed 40 seeded submissions. |
| 8 | Learning groups appear | PASS (API) / NOT TESTED (UI) | Four groups generated from the disposable class. |
| 9 | Teacher approval works | PASS (API) / NOT TESTED (UI) | One regular group approved in the end-to-end API flow. |
| 10 | Intervention generation and assignment | PASS (API) / NOT TESTED (UI) | One template activity generated, assigned to 8 group members. |
| 11 | Student activities | PASS (API) / NOT TESTED (UI) | Student list withheld answer keys; practice submitted and one assignment completed. |
| 12 | Reassessment submission | PASS (API) / NOT TESTED (UI) | Three fresh questions generated and answers saved; backend tests also cover scoring. |
| 13 | Progress analytics | PASS (API) / NOT TESTED (UI) | Class progress reflected one completed reassessment. |
| 14 | Language switching | PASS (key parity) / NOT TESTED (UI) | All 217 keys exist in each language; live language switching was not browser-tested. |
| 15 | Console/network errors | NOT TESTED | No browser DevTools audit was performed. |
| 16 | Production build/preview | PASS (HTTP) | `npm run build` passed; preview root, deep route, and API proxy returned 200. Visual flow not tested. |

### Automated checks

- `cd openpost/frontend && npm run lint`: passed with no warnings.
- `cd openpost/frontend && npm run build`: passed. Main JS chunk: 372.32 kB (117.58 kB gzip); largest route chunk (`ClassInsights`): 363.07 kB (105.04 kB gzip).
- `cd openpost/frontend && npm run i18n:check`: passed; 217 matching keys in English, Hindi, and Telugu.
- `cd openpost/backend && python -m pytest -q`: **56 passed, 1 skipped**. Two third-party deprecation warnings were emitted (`starlette.testclient`/`httpx` and Google GenAI typing).
- SQLite Alembic migration through `0004_submission_attempts`: passed. Offline PostgreSQL schema export was regenerated and checked for `attempt_no`.
- API end-to-end on a disposable seeded database: 40 diagnoses, 4 proposed groups, 1 intervention generation, 8 assignments, 3/3 correct practice answers, one completion, 3 reassessment questions, and a persisted 0/3 result for deliberately invalid reassessment answers.

### Negative/edge tests and audits

- Student answer-key withholding and ownership checks: covered by backend tests and confirmed during the API flow.
- Translation key parity: passed. Native-speaker review is still needed.
- Invalid student code: backend returns 404 in automated tests; live UI validation was not browser-tested.
- Empty states, network failure/retry visuals, double-click behavior, mobile widths, keyboard-only navigation, screen-reader behavior, and HTML-like evidence rendering: NOT TESTED in a browser.
- No frontend test runner is configured. No automated axe/Playwright checks were added.
- A prior command against port 8000 found a different/stale ClassPulse process exposing only health routes; it was left untouched. Current-source smoke/preview tests used port 8001.

## 8.8 Production build results

- Command: `cd openpost/frontend && npm run build`
- Exit code: `0`.
- Warnings: none.
- Main JavaScript chunk: 372.32 kB raw / 117.58 kB gzip.
- Largest route chunk, `ClassInsights`: 363.07 kB raw / 105.04 kB gzip.
- Preview check: ran on port 4187 because port 4173 was already occupied. `/`, `/teacher/progress`, and proxied `/api/demo/classes` returned 200. The preview was checked via HTTP, not through an interactive browser.

## 8.9 Known limitations

- Demo role selection and student codes are not authentication; do not expose this app on an untrusted network.
- Intervention generation auto-assigns to the approved group's members; there is no separate preview/assign API.
- Class progress lacks a per-student class comparison table and recent activity feed.
- The frontend does not have a dedicated reassessment list; a student opens reassessment from a completed activity.
- Hindi and Telugu have local translations, but every translation key needs review by a fluent speaker/educator.
- Responsive layouts, all form states, screen-reader behavior, and browser error handling were not manually verified.
- Assessment/intervention wording and the synthetic question catalog still need educator review for classroom use.
- No frontend unit or end-to-end test framework is installed.

## 8.10 Dependencies added

None. Existing React, React Router, Axios, Lucide, and Recharts dependencies were reused.

## 8.11 Translation review list

All Hindi and Telugu UI values should receive native-speaker and educator review; no formal translation review was performed. Key parity is verified, but matching keys do not establish translation quality.

## 8.12 Step-by-step hackathon demo procedure

This is the intended presenter flow; it has not been manually verified in a browser.

1. Start the SQLite-backed API and Vite frontend using the commands in **8.6**. Confirm the top bar reports the backend as connected.
2. Choose **Teacher** and the synthetic Fractions class. Run diagnosis twice if the API reports pending submissions because it processes a bounded batch. Open Class Insights to review provisional diagnoses, confidence, and evidence.
3. Open the teacher Interventions page, generate groups, and approve a regular M01–M05 group. M06 is reserved for diagnostic follow-up rather than standard remedial activity.
4. Generate and assign an activity. The existing backend creates assignments during generation; check the provider badge (the default local provider is template/mock).
5. Choose **Student**, select the same class, and use an assigned student code (for example `S001`; codes can be selected from the backend roster). Submit an assessment if needed, then open the assigned activity, submit practice, complete it, and answer the fresh reassessment.
6. Open My Progress as the student and Class Progress as the teacher. Describe score differences as observed changes with sample sizes, not proof that the activity caused a change.
7. Switch English/Hindi/Telugu from the language selector. The UI strings come from local JSON; backend-generated content remains in its source language.

If setup fails, check `/health`, confirm migrations/data import completed, verify `frontend/.env` uses the correct proxy target, and run `python scripts/smoke_api.py`.

## 8.13 Honesty statement

Displayed analytics, diagnoses, group membership, assignment statuses, answer evaluation, and progress values come from the backend. The frontend does not diagnose, group, or grade and does not render practice/reassessment answer keys before submission. Static copy, navigation labels, and the Fractions assessment title are product text rather than analytics. No Gemini calls were used in automated tests; the verified end-to-end activity reported the backend's `template` provider. Browser-level behavior remains unverified as noted above.
