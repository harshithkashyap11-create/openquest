# OpenQuest (ClassPulse AI) map and learning journey — current report

## Class navigation update — 2026-11-05

The Fractions run now also includes the five existing sample topics: Basic
algebra, Force and motion, Basic electricity, Grammar, and Subject-verb agreement.
Teachers can switch classes from the top bar. The running demo was updated by
adding the missing classes without resetting its existing Fractions responses.
Technical connection and repeated demo labels were removed from ordinary navigation;
the entry screen still identifies the classroom data as sample data. The recorded
backup below predates this interface update.

Date: 2026-11-05 (Africa/Nouakchott). **Local core implemented and verified;
independent educator evaluation remains NOT TESTED.** This is not a claim that
all MUST outcomes, a real classroom pilot, or the full seven-part request are
complete. The missing dependency is an approved, genuinely educator-labeled,
held-out dataset. A destructive reset is deferred in favor of fresh isolated runs.

## Outcome and data sources

| Feature | Route / command | Source and verification |
|---|---|---|
| Classroom Misconception Map | `/teacher/map` | Authorized persisted latest submissions, diagnoses and corrections; SQL counts, semantic concept list and bars; paginated original response evidence. No provider call when rendering. |
| Attention and uncertainty | Same map | All-date unresolved states, original confidence <0.75/status/missing quote and M06/FOLLOW_UP; no invented probability. Completed assignments determine reassessment readiness. Counts tested against source records. |
| Teacher decisions | Map evidence and Learning Evidence | Shared correction UI, explicit confirmation, versioned/idempotent existing API; original suggestion preserved, same-label review distinguished from changed-label correction. Lost acknowledgement retry verified. |
| Groups and selected support | Map concept → `/teacher/interventions?code=...#groups` | Existing persisted proposal/member/review/assignment flow. Backend rejects foreign members during approval and assignment. Group-wide support retains its existing confirmation. |
| Student journey/story | `/student/progress`, assessment and home navigation | Actual source submissions, support assignments, practice and reassessments. Reload verified. Missing events remain absent; no causal attribution or invented response-to-assignment FK. |
| Offline status | `/student/learning` | Existing IndexedDB queue and real sync acknowledgements; pending/synchronized/conflict/sign-in strings now localized. Full suite verifies offline save, reload and reconnect. |
| Workflow/data/local help and status | `/teacher/guide`, `/student/guide` | Verified data-handling explanation; local DB/config check without AI request or secrets. No support message is sent. |
| Held-out evaluation tooling | `python -m scripts.heldout_evaluation` | Strict local manifest, recorded outputs, frozen development-majority baseline and same held-out denominator; no source records supplied, so current status is NOT_TESTED with zero examples and null metrics. |
| Repeatable synthetic demo | `python -m scripts.run_map_demo` from backend | Fresh private SQLite run; six classes with 40 roster entries each, five Fractions assessment questions, varied saved Fractions answer patterns, and zero precomputed diagnoses. Other classes retain six learners with source answers and add 34 roster-only learners. Teacher-triggered diagnoses use the normal mock/template pipeline. Existing paths refused. |
| Recorded backup | `docs/upgrade-evidence/map-journey/2026-11-05-synthetic-fractions-mock.webm` | Recorded 2026-11-05, synthetic mock rules/templates, real browser operations and persistence. Accelerated automation; not live AI or human timing evidence. |

Normal runtime map/story data are persisted application records, not seeded UI
results. The fresh demonstration and browser fixtures are explicitly synthetic.
The evaluation artifact is a local status report, not a fabricated benchmark.
All interface additions are translated into en/hi/te; independent educator language
review is NOT TESTED. Original source/model text retains its stored language.

## Phase 0 audit and preserved state

Repository root: the OpenQuest checkout (the local workspace folder name is user-selected).
Branch `main`, HEAD `e99adf5` (one ahead of origin/main); clean initial working tree.
No project files changed until the user-facing Phase 0 report was presented.
No branch/worktree/commit/PR/push/deployment was created. The e99adf5 commit remains
HEAD and its FEATURE_IDEAS.md bytes remain unchanged; all 31 ideas are preserved.

Verified structure: `frontend/src/{App.jsx,pages,components,services,i18n}`;
`backend/app/{routes,schemas,models,services}`; `backend/alembic/versions`;
`backend/tests`; `frontend/tests`; `data`; `docs`; root `scripts`. No applicable
repository AGENTS.md/CONTRIBUTING instructions were found. The app is React 19 /
JavaScript / Vite with Axios/React Router/Recharts and FastAPI/SQLAlchemy/Pydantic,
SQLite/PostgreSQL and seven Alembic revisions. Active AI adapters are in backend
services (mock/OpenRouter/Gemini); the separate ai-service file is an unused
placeholder, not an active CrewAI system. ClassPulse remains the existing product
branding: no broad rename was attempted. Existing correction/group/intervention/
offline capabilities were reused. No current CI directory or configured standalone
type-check command was found. Source API inventory previously had an empty table;
new paths were verified directly against OpenAPI. Existing documented contract
paths/schemas were preserved byte-for-value in the updated JSON structures.

### Baseline versus final checks

Commands run in backend or frontend unless a different location is shown.

| Check / exact command | Baseline | Final |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` | PASS: 160 passed, 1 skipped; exit 0 | Final equivalent `python -m pytest -q`: PASS, 181 passed, 1 skipped; exit 0, 20.46s |
| `npm run lint` | PASS, exit 0 | PASS, exit 0 |
| `npm run i18n:check` | PASS, 577 keys/locale; exit 0 | PASS, 689 keys/locale; missing/extra/empty/interpolation checks, exit 0 |
| `npm run build -- --outDir /tmp/openpost-phase0-build` | PASS, exit 0; output outside repo | Final `npm run build`: PASS, exit 0 |
| `npm run test:e2e -- --list` | PASS: 22 discovered | Full suite has 24 tests |
| `npm run test:e2e -- tests/atelier.spec.js tests/quiz-workflow.spec.js --output=/tmp/openpost-phase0-safe-e2e --reporter=line` | FAIL: 19 passed, 1 failed; exit 1 | Baseline race repaired; see full suite below |
| `CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e -- --output=/tmp/openpost-final-e2e2 --reporter=line` | Full baseline NOT TESTED: original offline tests wrote screenshots into repository docs | PASS: all 24 passed; exit 0, 45.2s |
| `CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e -- tests/misconception-map.spec.js --output=/tmp/openpost-map-final --reporter=line` | New tests failed before map implementation | PASS: 2 passed; exit 0, 9.2s; includes lost acknowledgement, reload, keyboard/focus, languages/mobile and help/status checks |
| `CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e -- --config=playwright.demo.config.js --output=/tmp/openpost-demo-final --reporter=line` | New isolated rehearsal | PASS: 1 passed; exit 0, 16.1s for automated suite, not a timed human demo |
| `python -m scripts.run_map_demo` | Unavailable before this change | PASS: built frontend, bound local API 8019/preview 5189, fresh DB, health/proxy/class/map/status checks; long-running server has no completion exit code |
| `python -m scripts.heldout_evaluation --output ../docs/evaluation-status.json` | No held-out baseline runner | PASS: readiness artifact generated, exit 0; educational evaluation itself NOT TESTED |
| SQLite migration tests (inside full pytest suite) | PASS | PASS: empty upgrade/check, populated preservation, downgrade/re-upgrade; no new migration needed |
| PostgreSQL integration | NOT TESTED: disposable database not supplied | NOT TESTED; one integration skip remains |
| Live provider smoke | NOT TESTED; no external request made | NOT TESTED; all automated inference uses local mock/template providers |
| Human three-minute rehearsal / real-phone slow network | NOT TESTED | NOT TESTED |
| `git diff --check` | Clean initial tree | PASS, exit 0 |
| `git merge-base --is-ancestor e99adf5 HEAD` and feature-ideas byte comparison | PASS | PASS, exit 0; protected content unchanged |

The initial full browser baseline was stopped to honor read-only Phase 0 after
finding hardcoded screenshot destinations. A subsequent attempt encountered a
leftover test-server port; that owned process was stopped and the safe subset
rerun. No project files were changed in Phase 0. The actual pre-existing failure
was `atelier.spec.js: student practice, completion and reassessment keep real
scores and answers`: count() checked the completion button before an asynchronous
practice result arrived, skipped the click, then waited for reassessment. The test
now waits for the control and clicks unconditionally, retaining its score/reload
assertions. The React generated-practice list-key warning was fixed with stable
question index fallback. Screenshot outputs now use testInfo.outputPath, avoiding
repository writes during ordinary acceptance runs. Existing FastAPI/Starlette
TestClient deprecation and Node color-environment warnings remain informational.

New tests were observed failing before their implementations for map endpoints,
foreign-member review/assignment, evaluation loader, safe demo setup, status and
UI routing. The final demo also exposed a real late-refresh drawer reopening race;
selection now governs whether the drawer is open and success waits for reconciliation.

## Priorities, delivered scope and concrete deferrals (all 31 ideas)

The cut order was remote infrastructure → cross-subject identity → school reporting
→ roster/curriculum breadth → feedback aggregation. Core evidence, actual review,
student journey, truthful evaluation status and safe demo were retained.

| # | Idea | Priority / final scope and reason |
|---|---|---|
| 1 | Misconception Map | MUST / PASS: authorized aggregate and paginated evidence route. |
| 2 | Evidence | MUST / PASS: exact question/answer/explanation/suggestion fields. |
| 3 | Uncertainty/review queue | MUST / PASS: explicit persisted/deterministic rule; uncalibrated confidence. |
| 4 | Diagnosis correction | MUST / PASS: shared existing versioned API/UI, original output retained. |
| 5 | Group review | MUST / PASS: existing member/review route plus backend class validation. |
| 6 | Support from map | MUST / PASS: concept-filtered existing reviewed-group confirmation flow. |
| 7 | Attention today | MUST / PASS: actionable all-date counts; IST explained, no invented date cutoff. |
| 8 | Student story | MUST / PASS: source IDs, timestamps and actual assignment links. |
| 9 | Onboarding | SHOULD / PASS: skimmable in-app workflow guide. |
| 10 | Teacher control | MUST / PASS: suggested, reviewed, corrected and approved states distinguishable. |
| 11 | Report AI problems | SHOULD / DEFERRED: no general diagnosis-feedback owner/review workflow; correction/local help available. Add a separate authorized record/review owner before extending. |
| 12 | Reviewed languages | MUST / translation/key/mobile checks PASS; educator review NOT TESTED. Obtain actual bilingual educator review; original educational content is not silently translated. |
| 13 | Data explanation | SHOULD / PASS: actual DB/provider/device processing; no retention/encryption promise. |
| 14 | Educator evaluation set | MUST / NOT TESTED: no approved source labels; validated local manifest ready for genuine review. |
| 15 | Evaluation report | MUST / tooling/status PASS; held-out educational results NOT TESTED. Supply approved frozen source groups before computing model/baseline metrics. |
| 16 | Status | SHOULD / PASS: local DB/config; provider reachability explicitly untested. |
| 17 | Errors/retries | MUST / PASS for new map/correction paths: loading/empty/failure/retained data and lost acknowledgement replay. |
| 18 | Sync status | MUST / PASS: existing real queue/reconnect tested; localized states. |
| 19 | Support route | SHOULD / PASS: local teammate help; no invented contact or external delivery. |
| 20 | Hosting/backups | DEFERRED: remote infrastructure explicitly prohibited; no availability/backup claim. |
| 21 | Prepared demo | MUST / automated cycle, safe setup and recorded backup PASS; timed human rehearsal NOT TESTED. |
| 22 | Student journey | MUST / PASS: Assessment → Practice → Reassessment → Results navigation/story. |
| 23 | Unified profile | MAY / DEFERRED: class-bound identity cannot safely join subjects. Establish canonical membership first. |
| 24 | Roster import | SHOULD / DEFERRED: no current class-creation flow; adds breadth without enabling demo. Resume with preview/validation/confirmation and ownership. |
| 25 | Curriculum tags | SHOULD / DEFERRED: no authoritative grade/curriculum provenance. Obtain reviewed source taxonomy before additive fields. |
| 26 | Pilot controls | MAY / DEFERRED: recovery, retention/deletion and audit product flows exceed local scope; existing role checks retained. |
| 27 | Accessible assessment/practice | MUST / native semantics, keyboard/focus/mobile checks PASS; human screen reader/zoom audit NOT TESTED. |
| 28 | Synthetic reset | MUST safeguard / fresh-run isolation PASS; destructive reset DEFERRED because marker/name cannot prove every row is synthetic. Start a new run. |
| 29 | Deployment | DEFERRED: no remote deployment authorized. |
| 30 | School overview | MAY / DEFERRED: no school/admin authorization boundary. Establish tenancy before aggregates. |
| 31 | Usefulness feedback | SHOULD / DEFERRED: no general feedback ownership/aggregation model and no adequate sample. Keep it separate from educator reference labels. |

Missing-data/capability deferrals: educator reference set, stable cross-subject
identity, school tenancy, curriculum provenance, class-creation flow and a safe
mixed-database reset boundary. Hackathon cuts: general feedback product/pilot
controls and production infrastructure. The impact and safe resume path are in
the table; none is represented by a nonfunctional UI shell.

## Evaluation and localization/accessibility limits

Independent dataset size **0**, educator-labeled references **0**, held-out size
**0**. Existing CSV/ground-truth examples are engineering-authored synthetic
development material, not real classroom outcomes or independent educator labels.
The majority-label baseline is defined from development references before held-out
scoring; no baseline score is computed without data. Exact-match denominator keeps
all held-out records, including abstentions, malformed/missing outputs and provider
failures. Those output categories remain separate. Per-label support/F1, confusion,
subject/language counts, metadata and dataset digest are available for future
recorded runs. Nine deterministic tests use test-only synthetic fixtures to validate loader/accounting behavior;
they are not a project accuracy claim. No provider call or external upload occurs.

Language catalog checks: PASS for en/hi/te, 689 keys with interpolation parity.
360px map screenshots were inspected, including Telugu wrapping; desktop saved
progress was inspected at 1280px. Keyboard Enter selects concepts, Escape closes
drawers and focus returns; native labeled forms and status/alert semantics are
used. Existing reduced-motion and offline acceptance tests pass. Token contrast
calculations on light surfaces: body 14.72:1, secondary 7.58:1, brand 6.84:1 and
focus against app background 7.97:1. These are sampled token checks, not a full
accessibility conformance audit. Human screen-reader testing, all-theme contrast,
200% zoom, real Android/network throttling and educator language review: NOT TESTED.

## Architecture, storage and tooling

No new runtime dependencies, cloud infrastructure, message queues, global store,
chart library, schema fields or migration were added. Existing APIs persist all
mutations. Additive endpoints/read schemas are documented in API_CONTRACT.json
and API_INVENTORY.md. Existing architecture/limitations/database/demo/install/
language/privacy/evaluation docs were updated; FEATURE_IDEAS.md was not edited.

Skills actually used: brainstorming (scope from the detailed user contract; its
extra approval workflow was overridden by the user's explicit autonomous-execution
instruction), frontend-design (existing quiet teacher UI/tokens), frontend-a11y
(native controls/focus/status), api-design (bounded additive read APIs), security-review
(class ownership/source privacy), test-driven-development (failing acceptance checks),
systematic-debugging (baseline race and drawer reconciliation), python-patterns
(Pydantic/explicit errors/local scripts), verification-before-completion (observed
checks), and plugin-management (requested Ponytail lookup). No skills were installed.
No dedicated FastAPI skill was available; repository conventions were used.

Tools/packages actually used: exec_command/apply_patch for local inspection/edits;
existing pytest/FastAPI TestClient/SQLAlchemy/Pydantic for real local API tests;
existing npm/Vite/oxlint/Playwright for production UI/offline rehearsal and recordings;
view_image for visual inspection; ffprobe for recorded-media validation; Codex app
open_in_codex for a queued local preview; plugin-management search for Ponytail.
No subagents, remote review service, live provider request or deployment tool was used.

Ponytail was requested during implementation. No tool, installed skill or command
was found, and plugin searches for Ponytail and Pony Tail returned no matches.
**Ponytail was not used.** Its exact plugin-directory link is needed to identify
and connect it; no substitute plugin was installed or falsely attributed.

## Files changed

Frontend changes add the map, shared review UI, source chronology, guide and localized states; backend changes add read-only projections and membership validation. Tests cover the real persistence boundaries. Provider prompts/adapters and classroom datasets were not changed. New demo/evaluation scripts remain local.

### Frontend

- [frontend/src/App.jsx](../frontend/src/App.jsx)
- [frontend/src/components/AppShell.jsx](../frontend/src/components/AppShell.jsx)
- [frontend/src/components/DiagnosisReview.jsx](../frontend/src/components/DiagnosisReview.jsx)
- [frontend/src/components/PageStates.jsx](../frontend/src/components/PageStates.jsx)
- [frontend/src/components/StudentJourney.jsx](../frontend/src/components/StudentJourney.jsx)
- [frontend/src/i18n/I18nProvider.jsx](../frontend/src/i18n/I18nProvider.jsx)
- [frontend/src/i18n/en.json](../frontend/src/i18n/en.json)
- [frontend/src/i18n/hi.json](../frontend/src/i18n/hi.json)
- [frontend/src/i18n/te.json](../frontend/src/i18n/te.json)
- [frontend/src/pages/Assessment.jsx](../frontend/src/pages/Assessment.jsx)
- [frontend/src/pages/Intervention.jsx](../frontend/src/pages/Intervention.jsx)
- [frontend/src/pages/LearningEvidence.jsx](../frontend/src/pages/LearningEvidence.jsx)
- [frontend/src/pages/LearningLab.jsx](../frontend/src/pages/LearningLab.jsx)
- [frontend/src/pages/MisconceptionMap.css](../frontend/src/pages/MisconceptionMap.css)
- [frontend/src/pages/MisconceptionMap.jsx](../frontend/src/pages/MisconceptionMap.jsx)
- [frontend/src/pages/StudentDashboard.jsx](../frontend/src/pages/StudentDashboard.jsx)
- [frontend/src/pages/StudentProgress.jsx](../frontend/src/pages/StudentProgress.jsx)
- [frontend/src/pages/TeacherDashboard.jsx](../frontend/src/pages/TeacherDashboard.jsx)
- [frontend/src/pages/WorkflowGuide.jsx](../frontend/src/pages/WorkflowGuide.jsx)
- [frontend/src/services/learningApi.js](../frontend/src/services/learningApi.js)

### Backend / AI boundary

- [backend/app/main.py](../backend/app/main.py)
- [backend/app/routes/groups.py](../backend/app/routes/groups.py)
- [backend/app/routes/health.py](../backend/app/routes/health.py)
- [backend/app/routes/misconception_map.py](../backend/app/routes/misconception_map.py)
- [backend/app/schemas/misconception_map.py](../backend/app/schemas/misconception_map.py)
- [backend/app/services/auth_service.py](../backend/app/services/auth_service.py)
- [backend/app/services/intervention_service.py](../backend/app/services/intervention_service.py)
- [backend/app/services/journey_service.py](../backend/app/services/journey_service.py)
- [backend/app/services/misconception_map_service.py](../backend/app/services/misconception_map_service.py)
- [backend/scripts/heldout_evaluation.py](../backend/scripts/heldout_evaluation.py)
- [backend/scripts/run_map_demo.py](../backend/scripts/run_map_demo.py)

### Tests and verification scripts

- [backend/tests/test_heldout_evaluation.py](../backend/tests/test_heldout_evaluation.py)
- [backend/tests/test_map_demo.py](../backend/tests/test_map_demo.py)
- [backend/tests/test_misconception_map.py](../backend/tests/test_misconception_map.py)
- [frontend/demo-tests/fractions-demo.spec.js](../frontend/demo-tests/fractions-demo.spec.js)
- [frontend/playwright.demo.config.js](../frontend/playwright.demo.config.js)
- [frontend/tests/atelier.spec.js](../frontend/tests/atelier.spec.js)
- [frontend/tests/learning-intelligence.spec.js](../frontend/tests/learning-intelligence.spec.js)
- [frontend/tests/misconception-map.spec.js](../frontend/tests/misconception-map.spec.js)
- [scripts/check-i18n.mjs](../scripts/check-i18n.mjs)
- [scripts/run_quiz_test_api.py](../scripts/run_quiz_test_api.py)

### Data / local report

- [docs/evaluation-status.json](../docs/evaluation-status.json)

### Documentation / synthetic media

- [README.md](../README.md)
- [docs/API_CONTRACT.json](../docs/API_CONTRACT.json)
- [docs/API_INVENTORY.md](../docs/API_INVENTORY.md)
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- [docs/DEMO_GUIDE.md](../docs/DEMO_GUIDE.md)
- [docs/EVALUATION_METHODOLOGY.md](../docs/EVALUATION_METHODOLOGY.md)
- [docs/FINAL_IMPLEMENTATION_REPORT.md](../docs/FINAL_IMPLEMENTATION_REPORT.md)
- [docs/INSTALLATION.md](../docs/INSTALLATION.md)
- [docs/KNOWN_LIMITATIONS.md](../docs/KNOWN_LIMITATIONS.md)
- [docs/MULTILINGUAL_SUPPORT.md](../docs/MULTILINGUAL_SUPPORT.md)
- [docs/PRIVACY_AND_SAFETY.md](../docs/PRIVACY_AND_SAFETY.md)
- [docs/database_design.md](../docs/database_design.md)
- [docs/DEMO_GUIDE.md](../docs/DEMO_GUIDE.md)
- [docs/upgrade-evidence/map-journey/2026-11-05-synthetic-fractions-mock.webm](../docs/upgrade-evidence/map-journey/2026-11-05-synthetic-fractions-mock.webm)
- [docs/upgrade-evidence/map-journey/README.md](../docs/upgrade-evidence/map-journey/README.md)
- [docs/upgrade-evidence/map-journey/map-en-360.png](../docs/upgrade-evidence/map-journey/map-en-360.png)
- [docs/upgrade-evidence/map-journey/map-hi-360.png](../docs/upgrade-evidence/map-journey/map-hi-360.png)
- [docs/upgrade-evidence/map-journey/map-te-360.png](../docs/upgrade-evidence/map-journey/map-te-360.png)
- [docs/upgrade-evidence/map-journey/saved-progress.png](../docs/upgrade-evidence/map-journey/saved-progress.png)

## Final acceptance checklist

| Acceptance item | Status / evidence |
|---|---|
| Phase 0 before edits | PASS: clean-tree read-only audit and user-facing report preceded implementation. |
| Verified structure / no unnecessary rewrite | PASS: existing routers/services/components retained; changes are additive and focused. |
| Authorized persisted map data | PASS: API and required-auth isolation tests. |
| Count reconciliation | PASS: source totals/latest attempts/multiple suggestions and correction tests. |
| Evidence attribution | PASS: original response, quote, AI explanation and correction fields distinct. |
| Defined uncertainty | PASS: code/status/threshold/missing-quote rule documented; no calibration claim. |
| Discoverable persisted correction | PASS: map and shared Learning Evidence UI; confirmed/reloaded/idempotent. |
| Original AI output preserved | PASS: API and browser assertions. |
| Discoverable group review | PASS: concept-specific route and existing member/review UI. |
| Approval membership/authorization | PASS: foreign-member/credential tests; group minimum two. |
| Teacher-selected support persistence | PASS: existing explicit group confirmation and fresh-demo assignment. |
| Actionable attention counts | PASS: SQL counts and readiness transition tests. |
| Persisted reassessment readiness | PASS: completed assignment + absent/pending result; no elapsed-time inference. |
| Linked student story | PASS: source/assignment/result IDs and reload; response-to-assignment FK absence disclosed. |
| No causal story claim | PASS: explicit UI/doc caveat; existing sample-size context preserved. |
| AI/teacher decisions distinct | PASS: suggested/reviewed/corrected/approved labels reflect actual persisted records. |
| Feedback does not mutate diagnoses | DEFERRED: no new feedback persistence implemented. |
| Accurate student-data explanation | PASS: guide reflects actual DB/provider/IndexedDB handling. |
| Educator evaluation provenance/labels | NOT TESTED: no approved references supplied. |
| Untuned held-out records | NOT TESTED for a real set; tooling rejection checks PASS. |
| Same baseline/model held-out items | NOT TESTED for a real set; hand-counted accounting tests PASS. |
| Report counts/limitations | PASS: zero counts and null metrics; future report carries support and limitations. |
| Separate uncertain/invalid/provider failure | PASS for tooling tests; educational run NOT TESTED. |
| All new strings en/hi/te | PASS: key and interpolation/empty checks; human review NOT TESTED. |
| Missing translations visible/detected | PASS: checker plus development missing-key marker. |
| Keyboard/screen-reader semantics | PASS for native labels/status/keyboard/focus automation; human screen reader NOT TESTED. |
| Accessible chart information | PASS: bars and semantic concept list share the same counts. |
| Offline status matches queue/server | PASS: production offline/reload/reconnect acceptance tests. |
| Saved/queued/unknown messages | PASS in tested new flows and localized existing queue. |
| Retry duplication protection | PASS: real server save followed by lost acknowledgement and same-command retry. |
| Safe status payload | PASS: configuration-only provider status, no secrets or raw diagnostics. |
| Honest local support route | PASS: no invented contact or delivery claim. |
| Visible synthetic demo labeling | PASS: class and guide/recording labels; no precomputed suggestions. |
| Reset cannot touch real data | PASS for exclusive fresh-run alternative; destructive reset DEFERRED. |
| Real demo auth/persistence path | PASS: actual demo role entry, ordinary APIs and reload; demo auth limitation disclosed. |
| Backup visibly recorded | PASS: recording named/linked with date, mock provenance and limits. |
| Remote hosting/backups out of scope | PASS: no push, remote deployment or backup claim. |
| Stable unified identity | DEFERRED: no cross-subject profile added. |
| CSV preview/confirmation | DEFERRED: roster import not added. |
| Reliable curriculum provenance | DEFERRED: curriculum fields not added. |
| School authorization | DEFERRED: no school aggregates added. |
| Feature docs match implementation | PASS: current sections distinguish implemented/deferred/untested behavior. |
| Limitations updated | PASS: educator, language, confidence, offline, identity and demo limits explicit. |
| Exact demo setup/recovery | PASS: actual labels/routes/start command and recorded fallback. |
| DB docs match migrations | PASS: no migration added, head remains 0007. |
| Observed checks in report | PASS: commands/counts/exits and unavailable checks distinguished. |
| No unrelated cleanup/generated churn | PASS: diff reviewed; intentional OpenAPI additions and synthetic backup media only. |

How to demo, exact actions and recovery: DEMO_GUIDE.md. The local command was
executed successfully; it serves only the fresh synthetic database. Running the
command while those default ports are occupied will refuse the API port; stop the
previous run or choose distinct ports before creating another run.

No remote push, commit, PR, deployment or external student/evaluation data upload
occurred. Existing user work and e99adf5/FEATURE_IDEAS.md were preserved.

```bash
cd backend
python -m scripts.run_map_demo
```

---

# Historical implementation report (retained verbatim)

The following report describes an earlier upgrade. Its date, commit references,
counts and acceptance verdict are historical; the current status is above.

# ClassPulse AI — final implementation report

Date: 2026-11-03. **Verdict: READY WITH LIMITATIONS for a local, synthetic core
hackathon demonstration.** The full eight-part specification is not complete.
Independent educational evaluation, broad language validation, production deployment
controls and a timed human rehearsal must not be represented as verified.

## Repository and environment

Active repository: OpenQuest; product name: ClassPulse AI.
Inspected/final Git HEAD: `df1e0656931652d91dd292f0783b9bd93cb68375`; branch main,
with working-tree changes and additions. No commit or push command was issued by
this agent. Existing tracked and untracked work was retained. A source recovery
snapshot was saved before behavior changes; the relevant implementation history is available in Git.

Executed versions: Python 3.14.7; Node 22.23.1; npm 10.9.8; FastAPI 0.141.1;
SQLAlchemy 2.0.52; Alembic 1.20.1; Pydantic 2.13.5; HTTPX 0.28.1. Frontend manifests
retain React 19.3.1 and Vite 8.3.5. No new runtime dependencies were installed.

Migration head: `0007_learning_intelligence`, following the existing 0006 quiz
migration. SQLite empty upgrade, populated legacy-row preservation, model/schema
comparison and downgrade/re-upgrade were exercised on isolated files. The original
configured application database was not migrated or removed. PostgreSQL execution
of this new revision remains NOT TESTED.

## Reused foundation versus new implementation

Reused: React role navigation/design/i18n/reduced motion; class-scoped baseline
assessments; taxonomy/evidence-validated diagnosis; existing native Gemini and
OpenRouter transports; primary misconception groups; interventions and practice;
assignment-linked reassessment/progress; read-only Copilot and existing quiz /
reflection / repair workflows.

Added or materially connected:

- Durable student/topic evidence, optimistic learner/session projections, explainable
  heuristic mastery and bounded stored next-action decisions.
- Assessment/diagnosis/teacher review/assignment/practice/hint/completion/reassessment
  handoff to one learning evidence ledger, with retry identities and source links.
- Credential-backed accounts, HttpOnly cookie sessions, CSRF checks, teacher/student
  and classroom authorization, expiry/revocation and required-mode browser sign-in.
  Explicit local synthetic demo compatibility remains separate.
- Versioned structured Lesson Studio, target misconception correction, editable
  objectives/explanation/questions, review of keys/language, separate publication,
  archived history and pinned lesson links to matching approved activities.
- Four-level misconception-specific practice hints, plus opt-in live response-aware
  Gemini/OpenRouter guidance with provisional feedback, grounded excerpts, numeric
  answer-disclosure guards and actual generation provenance.
- Student Learning Lab, explicit downloads, static-only PWA shell, student-scoped
  IndexedDB and foreground practice synchronization with transactional receipts.
- Append-only teacher diagnosis corrections that preserve original model output and
  change future proposed groups without rewriting existing assignments.
- Dedicated synthetic demo initialization, private generated credentials, health /
  provider smoke commands, contract/schema exports, evaluation accounting and docs.

Verified defect fixes: reassessment questions no longer contaminate the baseline
bank; all practice responses must be saved before completion; identical completed
reassessment retries return their original results; corrected labels affect new
grouping proposals; Copilot fallback no longer inherits a live model identity;
static cache warmup accounts for Vite's Origin variation; animated route entry no
longer expands the mobile document horizontally; expected offline learning now
has a separate shell state instead of a misleading backend-failure banner.

## Architecture, persistence and API compatibility

See ARCHITECTURE.md for implemented component/sequence diagrams, LEARNER_MODEL.md for
update rules, and AGENT_ORCHESTRATION.md for transitions and action permissions.
The policy emits one finite recommendation per accepted event and never executes
model-generated SQL/tools or grants itself approval. Teacher membership review and
lesson review/publication are explicit. Difficulty is currently a recommendation,
not a validated adaptive question selection engine.

0007 adds twelve tables: auth_accounts, auth_sessions, learning_events,
learner_states, learning_sessions, learning_decisions, mutation_receipts,
diagnosis_corrections, lessons, lesson_revisions, lesson_reviews and assigned_lessons.
Existing learner/quiz tables are not dropped or rewritten. New tables protect
source references, topic uniqueness, retry keys and revision identity. Optimistic
updates and uniqueness violations return retryable 409 conflicts. A downgrade
removes the new history and therefore is appropriate only with a backup or on a
disposable database.

New endpoints are grouped under /api/auth, /students/{id}/learning-state,
/classes/{id}/learning-states and /lessons, /lessons/{id}/review and /assign,
/diagnoses/{id}/corrections, and assignment-bound tutor and sync-practice paths.
`/health/ai` reports configuration separately from live readiness. Existing routes
remain; assessment retry identity and group revision fields are additive. Required
mode intentionally rejects old unauthenticated access and requires group revision
checks. Complete method/schema inventory: API_INVENTORY.md and API_CONTRACT.json.
Schema inventory: DATABASE_INVENTORY.md. UI dependencies: FRONTEND_API_MATRIX.md.

The original one-subject/topic-per-class, one-class-per-student schema is preserved.
The demo contains three subject-specific contexts, not one unified school roster.
Quiz questions remain their own authored format; their records were not silently
reclassified into canonical subject-topic learner evidence.

## Important files by area

| Area | Important additions and integration points |
|---|---|
| Backend services | `learning_service.py`, `auth_service.py`, `lesson_service.py`, `adaptive_tutor_service.py`, `mutation_service.py`, `diagnosis_review_service.py`; existing diagnosis, grouping, intervention, reassessment and Copilot services extended |
| Backend routes/contracts | `routes/auth.py`, `routes/learning.py`, `routes/tutoring.py`, `schemas/learning.py`; existing classroom/group/diagnosis/health routes retained and extended |
| Persistence | `models/learning.py`, `models/access.py`, `models/lesson.py`, `alembic/versions/0007_learning_intelligence.py`, `backend/schema.sql` |
| Frontend | `LearningEvidence.jsx`, `LessonStudio.jsx`, `LearningLab.jsx`, `LearningParts.jsx`, `Learning.css`, `learningApi.js`, `offlineLearning.js`, existing login/session/API/layout/assessment integration and three locale dictionaries |
| PWA | `public/sw.js`, `public/manifest.webmanifest`, registration in `src/main.jsx` |
| Tests | Learning evidence, secure API, integrated cycle, tutor, corrections, Studio, offline sync, regression, demo initialization and metric tests; SQLite migration tests and `learning-intelligence.spec.js` |
| Scripts | `prepare_demo.py`, `provision_account.py`, `check_health.py`, `probe_ai.py`, `verify_live_lessons.py`, `verify_live_tutor.py`, `evaluation_metrics.py`, `export_contract.py`, `scripts/verify-account-ui.mjs` |
| Documentation | The twelve requested architecture/domain/safety/evaluation/installation/demo/limitations/report documents plus source-derived API/database inventories and `upgrade-evidence/agentic` |

## Provider and educational evidence

The private local environment selects native Gemini, requested/reported model
`gemini-3.5-flash-lite`. The configured OpenRouter path remains available and was not
silently substituted. Its actual live reachability was not separately re-tested.
Keys remain server-side, were not printed and are not included in the report.

Latest synthetic live smoke measurements:

| Operation | Coverage | Observed result | Wall-clock latency |
|---|---|---|---|
| Diagnosis transport/schema/taxonomy/evidence | Mathematics 2, Science 1, English 1 | 4/4 checks passed; contrasting fraction reasoning produced M01 versus CORRECT | 4220, 3198, 1715, 1437 ms; median 2456.5 ms |
| Targeted lesson generation | M01 English, Hindi, Telugu | Three HTTP 201 structured drafts, targeted correction and plain-text fractions inspected | 20494, 4127, 3984 ms |
| Live guided tutor | M01 Telugu, two progressive levels with a new learner response | Two HTTP 200 validated hints with provider/model provenance | 2086, 1516 ms |

Raw synthetic evidence: `upgrade-evidence/agentic/provider-smoke.json`,
`live-lessons.json`, `live-tutor.json` and `measurement-summary.json`. The latency
sample is small and includes local/network overhead; it does not support production
p95, throughput or SLA claims. No automatic smoke retries were used.

These are real external inference smoke checks, **not independently labeled
accuracy measurements**. Diagnostic precision/recall/macro-F1, calibration,
independent language evaluation and causal educational improvement are NOT TESTED.
EVALUATION_METHODOLOGY.md distinguishes the old development fixtures, synthetic
regression accounting and the human adjudication needed for independent evaluation.

Mock diagnosis identifies itself as mock; non-fractions mock inference abstains.
Deterministic hints and lesson templates identify themselves as templates. Failed
live tutor output does not consume a hint or silently become successful Gemini
inference. Lesson template fallback requires an explicit opt-in after provider
failure. No cloud inference runs offline.

## Verification evidence

Final automated commands and evidence files:

| Check | Result | Evidence |
|---|---|---|
| `cd backend && python -m pytest -q` | **160 PASS, 0 FAIL, 1 SKIP/NOT TESTED** | upgrade-evidence/agentic/backend-tests.log |
| `cd frontend && npm run build` | PASS | build.log |
| `npm run lint` | PASS, no lint diagnostics | lint.log |
| `npm run i18n:check` | PASS, 577 matching keys per locale | i18n.log |
| `CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e` | **22 PASS, 0 FAIL** in the final full run | browser-tests.log |
| Required-account browser checks | 3 PASS: teacher login/logout; student teacher-endpoint denial; expired-cookie return to login; zero page errors | account-ui.json |
| Health endpoints on the isolated running demo | 3 HTTP 200; live readiness deliberately not implied by configuration | health.json |
| `git diff --check` and literal UI key inspection | PASS | no whitespace diagnostics or missing literal keys |

Unit/integration and browser test-case totals: **182 PASS, 0 FAIL, 1 NOT TESTED**
(the skipped PostgreSQL integration case). Provider smoke calls, account checks,
health and static checks are reported separately rather than double-counted as test
cases. The backend logs contain an existing Starlette TestClient/HTTPX deprecation
warning. A clean dependency install, PostgreSQL execution and real Android testing
were not run.

The automated cycle saves an explanation, validates/persists diagnosis, updates
learner state, rejects intervention before approval, records approval/assignment,
views a hint, saves practice, completes eligibility, scores reassessment and shows
updated evidence. Browser tests additionally cover teacher publication, downloaded
Telugu lesson reload while disconnected, template hint progression, offline practice
queueing and actual server persistence after reconnection without mastery inflation.
Existing quiz, role navigation, focus, retry, language and reduced-motion tests pass.

During development, a full run exposed mobile animation overflow and an offline
test that incorrectly assumed no previously approved group. The layout containment
was fixed and the test now reuses verified existing groups/active assignments. Final
runs above include those checks; earlier failed runs are not represented as passes.

## Mobile and accessibility observations

A single headless Chromium entry-page profile at 360×780, 4× CPU throttling,
400 ms latency and 50 KB/s each direction observed LCP 5568 ms, CLS 0 and 146436
bytes of entry-route JavaScript after gzip. Long tasks: 469, 308 and 107 ms. This is
simulated local testing, not a physical inexpensive Android measurement. The LCP
shows additional slow-network optimization is needed; no claim of excellent mobile
performance is justified. INP, real-device memory pressure, TalkBack and an
independent accessibility audit are NOT TESTED.

Browser tests check 360px overflow, native control labeling, focus restoration,
keyboard navigation and reduced-motion behavior. New controls reuse the existing
design. Screenshots include offline-practice-360.png, synchronized-practice-360.png
and teacher-account-1440.png in the agentic evidence directory.

## Acceptance gates

P0 software core: **8 PASS** with the following scope; this does not assert every
numbered instruction in the original specification has been delivered.

| P0 gate | Status and observed scope |
|---|---|
| A: startup and persistent DB | PASS: production frontend, API, marked SQLite DB, health and repeat initialization |
| B: real Gemini across three subjects | PASS: latest four synthetic diagnosis checks; broad accuracy remains unmeasured |
| C: assessment → diagnosis → learner persistence | PASS: transactional API integration cycle and stored evidence |
| D: teacher-controlled approval | PASS: role/class/CSRF guards, revision checks and protected assignment tests |
| E: adaptive tutor and progressive hints | PASS: four-level bounded templates, response-aware live hint path, provisional feedback, actual hint ledger |
| F: Lesson Studio | PASS: generation/edit/review/publication/student retrieval plus pinned assignment links; translation synchronization/per-section regeneration remain incomplete |
| G: reassessment and progress | PASS: practice eligibility, independent scoring, idempotent retry and evidence update; no causal impact claim |
| H: deterministic demonstration path | PASS: connected API cycle and production browser learning flows; timed human three-minute rehearsal NOT TESTED |

P1: A evidence/provenance/uncertainty PASS; B correction/audit PASS; C independent
evaluation NOT TESTED; D multilingual delivery PASS for the documented M01/live
sample coverage, broader quality NOT TESTED; E downloaded content/queued practice
PASS for the tested foreground workflow, full conflict-resolution UI incomplete;
F local authorization checks PASS, production security assurance NOT TESTED.
P2 voice, guardian summaries and printable packs are not implemented / NOT TESTED.

## Handoff and remaining work

The local synthetic preview is at `http://127.0.0.1:5188`, API on loopback port 8018.
It uses the dedicated marked demo file with the existing configured Gemini provider;
seeded diagnoses remain clearly labeled synthetic fixtures. Initial/repeated seeding
produced three classes, six students, six baseline submissions and six fixture
diagnoses. SQLite integrity returned ok and foreign-key check returned no violations.
The private generated demo credentials are not included in this report.

Use INSTALLATION.md for exact installation, migration, seed, startup and verification
commands. DEMO_GUIDE.md supplies the three-minute script, exact navigation and safe
provider/offline recovery. KNOWN_LIMITATIONS.md lists incomplete functionality.
PRIVACY_AND_SAFETY.md distinguishes actual controls from operational requirements.

Next priorities: independently adjudicated evaluation; validated adaptive question
selection; multi-subject school memberships; broader regional templates and
translation revision handling; learner history backfill/reconciliation; pagination
and load testing; explicit offline conflict export/resolution; real-device
performance/accessibility; and secure deployment/account recovery/retention.

**READY WITH LIMITATIONS** is justified for the reproducible local synthetic core.
The system is not claimed to satisfy the entire eight-part package, to be production
ready, or to establish educational accuracy or improvement beyond the evidence above.
