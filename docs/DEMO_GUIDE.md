# Current Fractions map demonstration — 2026-11-05

This path uses **synthetic** source responses, local **mock/rule** suggestions and
labeled **template** practice. It makes no external AI request and demonstrates
software persistence, not classroom learning efficacy or live Gemini quality.
No educator-labeled held-out dataset is available: evaluation is NOT TESTED, with
zero examples and no computed metrics (`evaluation-status.json`).

## Start from a fresh isolated run

Existing Python/npm dependencies must be installed (see INSTALLATION.md). From
the repository root, run:

```bash
cd backend
python -m scripts.run_map_demo
```

This builds the frontend and starts the local API on 8019 and production preview
on 5189. Open http://127.0.0.1:5189. It creates a new private directory under the
system temporary directory; its exact database path is printed. The existing app
DB and `.classpulse-demo` are never opened. All six classes have 40 roster entries.
The Fractions class has learners DEMO-01..40 and five assessment questions.
DEMO-04..40 have complete answer sets with varied misconception patterns across
M01-M05; their diagnoses are not stored in advance. Basic algebra, Force and motion,
Basic electricity, Grammar, and Subject-verb agreement each retain six original
sampled learners with answers and add 34 roster-only learners. Teachers can switch
classes using the top-bar selector. DEMO-02 has an original 2/5 response; DEMO-03
has an insufficient-evidence response. No diagnosis, approval, intervention or
result is precomputed. DEMO-01 starts empty.

This command is an explicit local demo; role selection is self-asserted, not
production authentication. No key or connection is needed for mock inference.
Stop with Ctrl-C. To start over, run the command again: it creates a **new** run,
retaining the previous one. Destructive reset is not implemented. `--directory`
accepts only a nonexistent path and always refuses existing directories/symlinks.
Do not delete or reset any database during the presentation. If default ports are
occupied, use `--api-port 8020 --web-port 5191`; occupied ports are refused rather
than silently using another API. Startup does not touch source or configuration.

## Three-minute narration plan

The entire browser journey has a separate automated rehearsal; a timed **human**
three-minute performance remains NOT TESTED. Prepare the two role contexts before
the presentation if needed, and keep narration brief.

| Time | Real action and persisted checkpoint |
|---|---|
| 0:00–0:25 | On `/login`, choose Student → Mathematics → Fractions → Fractions, enter DEMO-01, Continue as student. Complete the five-question assessment with the learner's own reasoning and submit. Show **Your answers were submitted. Your teacher can now review them.** |
| 0:25–0:50 | Sign out; choose Teacher and the same class. On Teacher Overview click **Diagnose new answers**. Each action processes up to 20 answers; repeat until the prepared queue is reviewed. Open **Classroom Misconception Map**. Counts come from saved responses; mock suggestions are visibly provider-labeled. |
| 0:50–1:20 | Select the concept surfaced for the fraction-addition reasoning. Inspect DEMO-01's original answer, quote and original AI suggestion. Mock rules normally surface M01; do not promise that a live provider must return it. Inspect DEMO-03's follow-up signal separately if time permits. Explain model confidence is not accuracy. |
| 1:20–1:40 | Choose a supported Teacher decision, give a review reason, Review correction → Confirm and save. Show **Teacher decision saved.** Confirming the same code is **Teacher reviewed**; choosing another is **Teacher corrected**. Original suggestion stays visible. For the prepared M01 activity path, confirm M01 after inspecting the actual evidence. |
| 1:40–2:00 | Close the drawer. **Review groups and choose support** opens the existing filtered Interventions flow. Generate groups, View members, inspect DEMO-01/02, then Approve. Choose **Generate and assign intervention** and confirm the recipients. Assignment is saved only after the server response. |
| 2:00–2:40 | Sign out; re-enter DEMO-01. Interventions → Open activity → Try it. Complete the three fraction questions, Check practice answers, then Finish & reassess → Finish activity and start reassessment. Submit the independent check-in. |
| 2:40–3:00 | Open My progress. Show the saved response, assigned support, practice and reassessment events, then reload. A later result is an observation; it does not establish that support caused improvement. Finish with the teacher's remaining actionable review item and the evaluation limitation. |

Preparation keys for the deterministic M01 templates: practice `5/12`, `1/2`,
`7/8`; reassessment `11/12`, `7/10`, `13/24`. These are rehearsal notes, not student
API answer keys. The teacher UI exposes its existing authorized key view.

## Recovery and optional paths

- If diagnosis fails, the assessment is already saved. Stay on Overview, inspect
  pending work and retry; the map remains usable from persisted data. This demo
  explicitly uses mock rules, so do not describe it as a live provider fallback.
- If a review acknowledgement is lost, keep the same input and confirm again.
  The correction request identity and server receipt reconcile the saved result.
  A late refresh must not reopen a drawer that the teacher closed.
- If group support generation fails, retain the reviewed group and retry its
  existing action. Do not describe a generated preview as assigned until saved.
- Reload restores saved assignment/results. For a network interruption, retain
  answers and retry the same action. A fresh run never erases the failed run.
- Offline practice: while online, download an assigned activity in Learning Lab.
  Disconnect, save practice, reload, then reconnect and synchronize. The queue
  distinguishes device-only pending, server-confirmed, sign-in and conflict
  states. Reassessment, teacher review and new hints require connectivity.
- Workflow, data and help opens actual local status checks, data storage guidance
  and a local teammate support route. No report is sent externally.
- For educator evaluation readiness, run `python -m scripts.heldout_evaluation`
  from backend. Show NOT_TESTED and sample count 0; do not substitute regression
  metrics for independent evaluation.

The production full-suite checks cover the offline route separately. Interface
translations are present in en/hi/te and have not received independent educator
review. Original question/answer/model text remains in its recorded language.

## Recorded backup

[Recorded synthetic mock journey](upgrade-evidence/map-journey/2026-11-05-synthetic-fractions-mock.webm)
was captured on 2026-11-05. It shows actual persisted demo operations with local
rules/templates and accelerated browser automation, before the class selector and
wording changes. Announce that it is recorded
before playing it. It does not demonstrate live AI, real classroom data or human
timing. Keep it separate from the live application result data.

## Reproduce the automated fresh-demo rehearsal

```bash
cd frontend
npm run build
CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e -- --config=playwright.demo.config.js --output=/tmp/openpost-demo-check
```

The test uses a new disposable database, real role-selection UI, real saves,
normal diagnosis/group/intervention APIs and server grading. Its recording is a
recorded synthetic mock demonstration, not live inference or human timing evidence.

---

The previous broader lesson/tutoring demonstration is retained below as an
alternative. Its precomputed fixtures and provider requirements differ from the
fresh map flow above.

# Reproducible three-minute demonstration

Use INSTALLATION.md to initialize and start the dedicated demo. Select Mathematics
→ Fractions → Synthetic ClassPulse · Mathematics. Its CP-M01-01 and CP-M01-02
records are explicitly **hand-authored synthetic fixtures**, model
synthetic-fixture-v1 / provider mock. Science and English have separate contexts
because the existing schema scopes one subject/topic per class.

Keep a teacher tab and a student tab ready in separate browser profiles/contexts.
Use local demo mode only on loopback, or sign in with the generated local accounts.
For live inference, start the demo API with the existing configured provider and
run the bounded provider smoke check first. Do not reset the original database.

| Time | Navigation and spoken explanation |
|---|---|
| 00:00–00:20 | Teacher Overview then Learning evidence. Say: “ClassPulse AI identifies why students struggle, not just whether their answers are wrong.” Identify the saved M01 evidence and synthetic fixture provenance. |
| 00:20–00:45 | Student Assessment: submit “2/5” and reasoning “I added the numerators and denominators.” Teacher Overview: run diagnosis. Show evidence, provider/model and uncertainty in Class insights. If more baseline questions are present, prepare all responses before the timed run. |
| 00:45–01:05 | Teacher Learning evidence: show the new event, heuristic category, evidence count and bounded recommendation. Learning groups: generate a proposal. |
| 01:05–01:30 | Review the M01 group and approve its exact membership; generate the intervention. Open Adaptive Lesson Studio (or the M01 link in Learning evidence), choose Telugu, generate or reopen a labeled draft. Show objectives, correction and worked example. Review keys/language, approve, publish, and attach to matching approved activities. |
| 01:30–02:05 | Student Learning Lab: open the approved activity and request hint one, describe a step, request hint two. Switch UI language to Telugu for the M01 ladder. Show the template provenance, or explicitly select live AI for response-aware guidance. Both remain provisional and do not add independent mastery credit. |
| 02:05–02:35 | Submit the three practice responses, return to Interventions, complete the activity, then submit the independent reassessment. Show progress and the updated evidence history. M01 practice keys: 5/12, 1/2, 7/8. Reassessment keys: 11/12, 7/10, 13/24. These are preparation notes, not keys exposed to the student API. |
| 02:35–03:00 | Download the published lesson while online, disconnect, reload Learning Lab, and show the previously downloaded content. Say that new AI inference requires a connection. Finish on teacher control, multilingual access and traceable evidence. |

Real inference latency varies and lesson generation can exceed the allotted 25
seconds. Prepare an approved draft before the timed run and clearly identify it as
previously generated. Do not call that draft fresh live inference. A complete timed
three-minute human rehearsal has NOT been established; the deterministic API cycle,
production UI lesson publication and offline reload have automated evidence.

If inference is unavailable, show that the assessment is saved and retry later.
An explicitly requested labeled template can support lesson generation. Never
present template/rule output as Gemini. Mock diagnosis for Science/English abstains;
show live subject smoke evidence separately or switch to the synthetic teacher-
reviewed fixtures with an explicit disclosure.

Recovery:

- Browser reload: saved attempts, decisions, hint history, lesson revisions and
  published links come from the database. Unsaved editor keystrokes may need to be
  entered again; click Save new revision before switching workspaces.
- Retry a lesson command with unchanged settings: the frontend reuses its pending
  request identity. A changed command receives a new identity.
- Retry a reassessment: identical saved answers return the prior result. Different
  answers conflict and cannot replace a completed score.
- Offline practice: download the activity, save responses in Learning Lab, reconnect
  and synchronize. Pending/conflicting responses stay on the device; server scores
  are authoritative. Logout refuses to silently discard unsynchronized work.
- Restart: stop only the demo process, restart using the same marked demo file,
  reload the browser. Seeding again preserves records and does not duplicate them.

Troubleshooting: /health is liveness, /health/ready checks DB access, /health/ai is
configuration only. Missing keys or provider 429/503 are separate from DB failure.
Use Vite's configured same-origin proxy; do not add permissive CORS as an emergency
fix. If migrations are missing, inspect the chosen DB and run the documented
additive migration; do not delete data. No emergency manual SQL edits are required.
