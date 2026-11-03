# ClassPulse AI upgrade — 2026-11-03

## Inspected baseline

Active repository: `/home/harshithkashyap/Desktop/open quest/openpost`, branch
`main`, revision `acquire with git rev-parse HEAD` (recorded in final report).
Sibling `openquest` and `classpulse_phase1` are historical material, not Git roots.
The Node backend is archived under `legacy/`. No repository AGENTS.md was found.
Existing tracked and untracked edits were preserved. Recovery source snapshot:
`/tmp/classpulse-baseline-nsoa44gl/source.tar.gz`; this excludes private environment
files, databases, dependencies, and the large historical screenshots.

React 19 / Vite 8 / JavaScript routes use `DemoSessionContext`, centralized Axios
services, English/Hindi/Telugu JSON resources and lazy page imports. FastAPI uses
synchronous SQLAlchemy sessions, SQLite locally, optional PostgreSQL, and Alembic
revisions 0001–0006. Startup does not apply migrations automatically.

| Capability | Source / route | Baseline observation |
|---|---|---|
| Class selection | `pages/Login.jsx`, `/api/demo/*` | Explicit synthetic demo identity; no credential verification |
| Baseline assessment | `classroom_service.py`, `/students/{id}/assessment-submissions` | Whole topic question bank; persisted attempts; no retry key |
| Diagnosis | `diagnosis_service.py`, `/classes/{id}/diagnose` | Bounded batches, taxonomy and verbatim evidence checks; provider outside async event loop |
| Provider | `gemini_client.py`, `openrouter_client.py` | Actual local selection is native Gemini, both credentials present; no values copied |
| Group review | `grouping_service.py`, `/groups/{id}/review` | Persisted group approval; no authenticated teacher enforcement |
| Intervention | `intervention_service.py`, `/groups/{id}/interventions/generate` | Approved groups only; subject templates and explicit generation provenance |
| Practice | `intervention_assignment_service.py` | Mutable per-question practice result; baseline has no tutoring event ledger |
| Reassessment | `reassessment_service.py`, `/reassessments/{id}/submit` | Assignment-linked checks and stored correctness; completion route needs eligibility guard |
| Progress | `progress_service.py`, teacher/student progress pages | Computed from stored baseline and reassessment records |
| Copilot | `copilot_context.py`, `/api/copilot/*` | Read-only contextual service; baseline routes lack authenticated class isolation |
| Quizzes | `quiz_service.py`, `quiz_tutor.py`, quiz pages | Existing uncommitted quiz/reflection work retained as a separate question format |
| Learner model / agent | none | Missing durable evidence projection and allowlisted decisions |
| Lesson Studio | quiz lesson suggestion only | Missing structured revision, language review and publication lifecycle |
| Offline | no manifest or service worker discovered | Offline claims unsupported at baseline |

Existing schema includes teachers, classes, students, questions, submissions,
diagnoses, learning_groups, group_members, interventions, intervention_assignments,
practice_responses, reassessments, reassessment_questions, reassessment_results,
quizzes, quiz_attempts and quiz_reflections. Student belongs to one class; each
class currently has one subject/topic. Multi-subject teaching is represented by
separate subject-topic classes; do not silently change that contract.

## Baseline execution

- `python -m pytest -q`: **137 passed, 1 skipped**; Starlette httpx deprecation warning.
- Bare `pytest -q`: import-path failure (`app` not found); use module invocation.
- `npm run build`, `npm run lint`, `npm run i18n:check`: **PASS**.
- No baseline real inference or browser workflow was reverified yet. Historical
  screenshots and logs are preexisting evidence, not evidence for this upgrade.

## Authorized implementation sequence

The attached eight-part specification supplies the design. Extend the existing
services with additive tables and migration 0007; preserve existing UI and routes.
1. Immutable evidence events, reproducible topic state and bounded decisions.
2. Optional credential-backed local sessions with fail-closed shared deployment;
   keep explicitly labeled local demo compatibility.
3. Versioned teacher-reviewed lessons and assignment-bound progressive tutoring.
4. Frontend evidence, lesson review and tutoring controls using existing styles.
5. Downloaded lessons and idempotent queued practice, only after core checks pass.
6. Isolated demo, reproducible checks, truthful evaluation and acceptance report.

Security and accessibility skills apply to the added endpoints and controls.
Tests must exercise persistence and rejected operations, not just source presence.
Real model evaluation is separate from deterministic tests and synthetic demos.

## Updates

Implementation and final execution evidence will be appended here and summarized
in `FINAL_IMPLEMENTATION_REPORT.md`. Do not interpret this plan as completion.
