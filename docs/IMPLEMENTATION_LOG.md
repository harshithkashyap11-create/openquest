# ClassPulse AI upgrade — 2026-11-03

## Inspected baseline

Active repository: `/home/harshithkashyap/Desktop/open quest/openpost`, branch
`main`, revision `df1e0656931652d91dd292f0783b9bd93cb68375` (inspected revision; working tree contains additions).
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

## Implemented and observed

- Added a replayable topic evidence ledger, optimistic learner/session projections,
  finite state transitions and one deterministic recommendation per event.
- Added credential-backed local sessions and class/role isolation, with separate
  explicitly local demo compatibility. Shared environments reject demo mode.
- Added structured versioned lessons, manual answer/language review, publication,
  historical revision retention and pinned links to approved activities.
- Added assignment-bound four-level practice hints, real hint history and practice
  evidence. New tutoring templates are labeled, not represented as live Gemini.
- Connected assessment, diagnosis, teacher review, approved assignment, practice,
  completion and reassessment to the same evidence projection.
- Corrected preexisting baseline-bank contamination by reassessment questions;
  added identical-reassessment retry handling and eligibility guards.
- Added student-scoped downloaded lessons/practice, foreground synchronization
  receipts, retained conflicts and static-only service-worker caching.
- Preserved the original quiz workflow, role UI, existing source changes and provider
  selection. A recovery snapshot exists; no commit/push command was issued.
- Full backend checks at an intermediate gate: 156 passed, 1 PostgreSQL skip.
  Full production browser gate: 21 passed. Final counts are recorded separately.
- Live native Gemini smoke: Maths/Science/English and contrasting fraction reasoning.
  Live M01 lesson generation: English/Hindi/Telugu. These are synthetic smoke checks,
  not independent diagnostic accuracy or verified school learning gains.
- Initial live lesson output was too general. Prompt context now includes canonical
  misconception meaning, objective and an explicit correction field; sampled new
  output targets fraction addition. Unsupported LaTeX is rejected by the schema.
- Offline browser check initially failed because Vite varies static assets by Origin.
  Cache matching was corrected only for same-origin static assets. The browser then
  reopened a downloaded Telugu lesson after disconnect/reload.
- All migrations/fixture tests use isolated files. The original configured database
  was not migrated or cleared. Dedicated demo initialization was executed twice.

See FINAL_IMPLEMENTATION_REPORT.md for final execution evidence, remaining gaps and
acceptance status. Optional capabilities and unverified deployment claims remain
explicitly incomplete in KNOWN_LIMITATIONS.md.

## Final verification and handoff

Final backend suite: 160 passed, one PostgreSQL integration skip. Production
browser suite: 22 passed, including real offline download/reload/queue/sync.
Separate credential-mode browser checks passed for teacher logout, student
authorization and expired-cookie recovery. Live synthetic tutor, diagnosis and
multilingual lesson checks have recorded actual provider/model/latency evidence.
Visual QA additionally caught the app shell's misleading backend-failure banner
during expected offline use; the shell now tracks connectivity separately and
the browser test asserts that state.

All twelve requested handoff documents exist. Local demo source was restarted on
loopback 8018 with its dedicated persistent database; production preview is on
5188. This is READY WITH LIMITATIONS for the local synthetic core, not completion
of every numbered requirement. Independent evaluation and operational limitations
are explicit in the final report.
