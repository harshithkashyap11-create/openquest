# Classroom Studio implementation brief

Checkpoint: `13fea7a`. Research date: 2026-11-05.

The user authorized research and implementation of the public product patterns below,
plus username-first demo sign-in with any nonempty password. Existing React/Vite,
FastAPI, SQLAlchemy and Alembic remain the foundation. SQLite already provides SQL
storage; PostgreSQL remains supported.

## Research method and provenance

Used the GitHub operations skill to inspect https://github.com/morluto/rea and its
browser-scenario contract. Used the installed `reverse-engineer-anything` skill and
REA `capture_browser_scenario` with a temporary headless Chrome, a declared navigation,
and accessibility capture. These were read-only public pages; no competitor account
was created and no private backend, model, or database was recovered.

| Public source | Observed capability | Original ClassPulse implementation |
|---|---|---|
| https://www.eedi.com/products and https://www.eedi.com/teach | Diagnostic bank, distractor signals, rotating response cards, bounded tutoring | Searchable starter bank and teacher-authored saved activities; printable rotating QR cards; persistent sessions and response counts; existing bounded tutor |
| https://help.formative.com/en/articles/12037990-ai-supported-features-in-formative | Multiple question types, PDF parsing, reviewable generation and feedback | Structured activity editor, answer-key grading, text-PDF preview, generated drafts, manual grading and standards reports |
| https://help.snorkl.app/en/articles/12615061-what-is-snorkl | Voice, whiteboard and text explanations with feedback | Persisted recordings, drawing strokes, editable speech transcript and text feedback; originals available to the teacher |
| https://help.snorkl.app/en/articles/13922081-what-s-new | Sequenced activities, progression rules and work exports | Ordered activity sets with server-enforced unlock thresholds; work PDF and grade CSV exports |

REA evidence identifiers: Eedi `ev_12c00500487afc4792379eec33d2c9303b9e137c7cdde57e83bf50633f9dc525`,
Formative `ev_281d0c530d8b9a26fb976280178fc4cacd507664dec30acec4a77cab1c225dc7`,
Snorkl `ev_8a700e30f63a094448ad3202a436aac647456893f34dc337735d943b65f7b964`.

Only public behavior/documentation is established. Internal algorithms, APIs,
training data, proprietary content and educational effectiveness remain unknown.
The starter bank uses original project content, not copied competitor questions.

## Delivery design

- Demo login accepts `math1`, `science1`, `english1`, `teacher1`, or `S1`/`student1`/
  existing demo roster code, with any nonempty password. Math/science/English
  accounts list one teacher's matching subject classes. Student aliases expose
  an explicitly synthetic course collection mapped to actual class-bound roster
  records. Required-auth accounts continue using existing credential validation.
- Sign-in opens My courses before any chapter dashboard; both roles can return
  to courses and switch only within their returned collection. Existing links
  remain usable with their current selected class and student record.
- New Classroom Studio activities coexist with legacy quizzes and assessments.
  Activities are editable drafts, immutable once published. Keys are omitted
  from student delivery and deterministic grading uses the teacher's keys.
- Supported response formats: single/multiple choice, true/false, number,
  short answer, writing, matching and categorizing. Free writing is marked
  pending teacher review. Drawing and audio accompany written reasoning.
- Submissions retain revisions, request identity and feedback; activity sets
  define ordered unlock rules; QR sessions store actual class answers.
- Standards are teacher-entered labels or explicitly custom starter identifiers.
  Reports show observed points and response counts, not validated mastery.
- PDF import previews extracted text and editable questions before saving.
  Text PDFs are supported; image-only scans need OCR and are reported clearly.
- PDFs and CSVs export actual stored work. The optional LTI AGS score publisher
  supports configured automatic or manual delivery; live LMS registration, tokens
  and identifier mappings must be supplied separately.
- AI generation/feedback uses the existing configured provider and labels template
  mode. Native Gemini feedback can receive original audio/drawings alongside text;
  other providers use text/transcript. One synthetic text-and-drawing live request
  succeeded; this is transport evidence, not educational validation.

## Acceptance

Exercise arbitrary-password demo login and course filtering, both-role course
switching, all grading formats, immutable publication, answer-key exclusion,
retry-safe revisions, teacher grading, set unlocks, QR aggregation, PDF import/
export and standards counts. Run existing backend and browser suites, build,
lint, migration drift and language checks. Real-device camera/microphone and
external LMS delivery must be reported separately from synthetic browser tests.
