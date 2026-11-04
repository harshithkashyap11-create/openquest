# ClassPulse AI — a three-minute demonstration

Use labeled synthetic demo records. This is demo role access, not production authentication. Keep provider provenance, uncertainty and observed sample sizes visible throughout.

## Verified environment and preparation

On 2026-11-02 the existing ClassPulse API was reachable at `http://127.0.0.1:8011`; port8000 belonged to another service. Read-only smoke checks passed, and the backend/frontend were restarted and smoke-checked again on2026-11-03. All six catalog classes exist: Fractions (40 synthetic learners), Basic algebra, Force and motion, Basic electricity, Grammar and Subject-verb agreement (6 each). The existing database had submissions but **zero diagnoses, groups, assignments and reassessments**. Do not imply those later stages are already prepared.

The configured provider is Gemini and a server-side key is configured. No live request was made during this UI upgrade. A configured key is not proof of provider availability. OpenRouter is also supported by the unchanged backend. Never show environment files or browser developer tooling that exposes private configuration during the demonstration.

Before presenting, choose one of these accurate modes:

- Existing backend: open a synthetic class and run the real Diagnosis action until the pending count reaches zero. Review the evidence, generate groups, inspect members, approve a suitable group yourself, and use the explicit Generate and assign confirmation. Complete one of those learners' practice/reassessment journeys before the event if progress must be available. These are genuine persisted operations, not UI fixtures.
- Deterministic fallback: from `frontend/`, run `python3 ../scripts/run_quiz_test_api.py` in one terminal. This existing harness creates an isolated temporary SQLite database with the synthetic catalog and `AI_PROVIDER=mock` on8012. In another terminal run `CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8012 npm run dev -- --host 127.0.0.1 --port 5173`. Prepare the same workflow through the UI. Keep the API terminal running: its temporary records disappear on exit. Clearly call this the mock/template demonstration.

Confirm `/health`, `/api/demo/classes`, the frontend, the selected role/class, the provider label returned by a real operation, one approved group, one assigned learner, and one completed reassessment before starting the timer. Do not import or change actual student records for presentation. The browser acceptance tests provide reproducible examples of these operations against a disposable mock database.

## Timed walkthrough — 175 seconds

| Time | Working action | Explain the value |
|---|---|---|a
| 0–20s | Entry → Teacher → Mathematics → Fractions → the actual class | “ClassPulse helps teachers understand student reasoning and choose the next teaching step.” Point to the live catalog: Mathematics, Science and English. |
| 20–50s | Overview → Class insights → View evidence | Show actual submission/diagnosis counts; open the evidence drawer. The quote supports the model interpretation. Confidence is an estimate; provisional and follow-up labels remain visible. Escape returns focus. |
| 50–85s | Learning groups → View members → a prepared intervention | Explain that teachers review groups. If demonstrating a new assignment, read the confirmation: this backend generates **and assigns** to approved members. Success appears only after the server responds. Identify the returned provider/teamplate label. Generated educational text still needs educator review. |
| 85–120s | Open Copilot → summarize the current class → request a short worksheet or plan | Show the selected class context, actual response and provider. Show the teacher-review draft banner. Close and reopen to demonstrate conversation retention. If the provider fails, use the visible retry state or disclose mock fallback; do not call a stored/fixture reply live AI. |
| 120–150s | Exit demo → Student → same class → a verified code → prepared activity | Show Learn & example, Try it, then Finish & reassess. Or open an assessment and move Next/Previous: answers remain. Do not submit a new attempt merely for animation. |
| 150–175s | Progress → show initial/follow-up samples → switch Telugu → Lite effects | “These are observed scores from different questions and sample sizes, not proof of a causal effect.” Finish: “Understand learning gaps, then help teachers act.” |

## Honest degraded demonstrations

If no diagnosis data exists, demonstrate the real pending state and run diagnosis; do not show empty charts as finished analysis. If no reassessment exists, show Not available and explain what must happen next. The baseline and final screenshots in `docs/upgrade-evidence/` are engineering evidence and are not a live demonstration. The test-run reassessment scores include deliberately incorrect answers; never describe them as evidence of improved learning.

If the backend is offline, show the explicit connection failure and retry action. This frontend has no pre-existing PWA/offline submission implementation. If live generation is unavailable, disclose mock/template mode. Keep a prerecorded walkthrough labeled prerecorded, and do not pretend a screenshot is functioning software.

## Run commands

From `openpost/backend/`, with the existing configured environment and database:

```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

From `openpost/frontend/`:

```bash
CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8011 npm run dev -- --host 127.0.0.1 --port 5173
```

If the API is already running on8011, reuse it. No migration, database reset or secret copying is required for the UI upgrade. Existing backend migration/import instructions remain in the repository README for a new environment.
