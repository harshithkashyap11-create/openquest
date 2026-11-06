# Classroom Studio and course login

Implemented 2026-11-06 on the checkpoint `13fea7a`.

## Try the demo

The running isolated preview is http://127.0.0.1:5191/login, API port 8021.
It uses `.classpulse-demo/studio-2026-11-06/fractions.sqlite`, separate from the
configured application database. The demo has six topics, 40 roster entries per
topic, 12 labeled sample Studio activities and six pathways. The two saved answers
used for visual review were submitted through the actual student UI.

| Role | Username | Password | Course collection |
|---|---|---|---|
| Mathematics teacher | `math1` | Any nonempty value, e.g. `*` | Fractions and Basic algebra |
| Science teacher | `science1` | Any nonempty value | Force and motion and Basic electricity |
| English teacher | `english1` | Any nonempty value | Grammar and Subject-verb agreement |
| Teacher demo | `teacher1` | Any nonempty value | Existing classes belonging to the selected demo teacher |
| Student | `S1`, `student1`, `S2`, etc. | Any nonempty value | Synthetic course collection mapped to class roster records |

Sign in, select a course, then open **Classroom Studio**. **My courses** returns
to the collection; the class picker switches within it. Demo aliases group the
same ordinal across sample rosters; this is not a new school enrollment system.
Existing required-auth accounts continue using their real password and assigned
classes. The any-password route is available only in `AUTH_MODE=demo`.

For a fresh isolated demo, run from `backend` using unused ports:

```bash
python3 -m scripts.run_map_demo --api-port 8022 --web-port 5192
```

This creates a new SQLite database, runs Alembic, seeds the sample data and builds
the frontend. Existing runs are retained. It uses explicitly labeled mock/template
feedback so a presentation does not depend on provider availability.

For an existing development database, back it up, install
`backend/requirements.txt`, run `python3 -m alembic upgrade head`, and restart the
API. The new head is `0008_classroom_studio`. No existing table or learner record
is rewritten by that migration.

## Features

| Area | Current behavior |
|---|---|
| Question library | Twenty original starter items across six topics, with deliberate distractors and custom `CP.*` labels. Teachers can save their own validated questions and reuse them in drafts. Queries return up to 100 saved items per course topic. These are not copied competitor questions or certified curriculum standards. |
| Activity editor | Single choice, multiple selection, true/false, numeric with tolerance, short answer, writing, matching and categorization. Teacher keys, hints, explanation, standards, point values and attempt limits are editable before publication. Published content stays fixed; editing a published activity creates a copy. |
| Generation | Existing Gemini/OpenRouter provider creates reviewable drafts. Template mode reuses original starter questions, does not alter difficulty, and may offer fewer items than requested when the small starter bank is exhausted. Generation errors preserve the current draft. |
| PDF import | Up to 7 MB and 30 pages. Selectable text is extracted locally. Numbered questions with lettered options, `Answer: B` and optional `Explanation:` become editable suggestions. Original extracted text is visible. Teachers supply missing keys. Image-only scans require external OCR. |
| Student reasoning | Text, canvas strokes, a recording up to 60 seconds, playback and editable transcript. Browser speech recognition is optional and browser-dependent; it may use an online service. Original evidence is saved with each attempt. |
| Feedback | Bounded five-exchange reflection, exact text-quote validation and explicit uncertainty. Configured native Gemini also receives the saved drawing/audio; OpenRouter and templates use text/transcript. Provider provenance and actual input modes are retained. Feedback cannot change grades. |
| Grading | Deterministic teacher-key grading; fractional numbers are supported. Writing remains pending until teacher review. Teachers can review points and comments. Attempts are retained; retrying an identical command does not duplicate it. |
| QR response room | Class-specific printable cards, A/B/C/D identified by card orientation, a browser camera scanner, manual entry, persistent counts, resuming and closing sessions. Repeated scans update one response per student. These session responses are distinct from a student's submitted assessment. |
| Pathways | Teacher orders published activities and sets a minimum percentage. The server checks earlier completions before accepting later work. Pending teacher grades do not unlock a score gate. Activities belong to one pathway to avoid contradictory cycles. |
| Reports | Original work, recordings, drawings, comments and conversations. Standards totals use latest attempts; pending review is counted. Points do not establish mastery. The existing teacher Copilot receives bounded Studio counts and standards, excluding recordings, drawings and conversation text. |
| Exports | Work PDF includes the selected answer text, reasoning, drawing, teacher feedback and saved conversation. Recordings remain playable in Studio rather than embedded in the PDF. Grade CSV uses each student's latest attempt and escapes formula-leading cells. |
| LMS | Configured LTI AGS final-score publishing, automatic or teacher-triggered, with persisted delivery receipts and retry status. A controlled HTTP test validates the score contract. A real LMS is not connected. |

## Optional LMS delivery

Supply these backend environment values after obtaining an LMS-scoped access token
and an existing line item. They can also be passed through Compose. Keys in the
two maps are ClassPulse UUIDs, not display codes.

```dotenv
LMS_ACCESS_TOKEN=
LMS_LINEITEMS={"ACTIVITY_UUID":"https://your-lms.example/lineitems/123"}
LMS_USER_IDS={"STUDENT_UUID":"LMS_LEARNER_ID"}
LMS_AUTO_PASSBACK=false
```

Automatic delivery occurs after a fully scored submission or a teacher review.
Manual delivery is available in Reports. Older attempts cannot overwrite the
latest one. A successful receipt prevents identical resend; network uncertainty
retains the timestamp for retry. Local grades remain saved if delivery fails.
The adapter does not implement LTI launch, OAuth token acquisition/refresh,
dynamic registration, roster synchronization or line-item creation. Those require
the target LMS's registration details. Protocol reference:
https://www.imsglobal.org/spec/lti-ags/v2p0/#score-publish-service.

## Evidence and limits

Research method, sources and REA evidence IDs are in
[COMPETITOR_RECONSTRUCTION.md](COMPETITOR_RECONSTRUCTION.md).
Raw REA records and local screenshots/PDF are retained in the ignored
`docs/upgrade-evidence/studio/` directory.

One live Gemini synthetic text-and-drawing request succeeded in 2,363 ms, with
verbatim text evidence. Recording storage/playback is exercised with a synthetic
audio stream in a real browser MediaRecorder. Camera decoding is tested using
real QR images rotated through all four orientations. Physical classroom camera
scanning, real microphones, live audio interpretation, language quality, educator
diagnosis accuracy, learning impact and real LMS delivery are not established by
those checks. PostgreSQL DDL is generated, but execution requires a disposable
PostgreSQL test database.

This implements the public workflow patterns in the existing app. It does not
recover competitors' private models, proprietary content or historical datasets.
The Studio activity loop remains separate from legacy quiz and learner-state
records; Copilot counts connect them at the class context level. New Studio media
submissions require connectivity; the existing offline practice feature remains
available for its original assignment formats.
