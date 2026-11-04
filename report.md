# ClassPulse AI — Build Report

**Prepared:** November 3, 2026

**Product:** ClassPulse AI, a classroom learning and formative-assessment platform

## What we built

ClassPulse AI is a web app for teachers and students that connects assessment,
explanation-aware diagnosis, teacher-reviewed support, practice, and reassessment.
It is designed to help a teacher understand how a learner reached an answer and
choose a next instructional step. It is a working software prototype with synthetic
demo data; it has not been validated as an educational intervention or as a
production school system.

## Teacher experience

- **Class overview and insights:** Review assessment activity, submissions,
  misconception diagnoses, follow-up cases, groups, interventions, and progress.
- **Assessment and diagnosis:** Students submit answers and explanations. The API
  stores attempts and can request structured, topic-aware diagnoses with supporting
  evidence and uncertainty information.
- **Teacher-controlled grouping:** Generate proposed groups, inspect membership,
  and approve or reject them. The system does not assign an intervention from an
  unapproved group.
- **Interventions and progress:** Prepare targeted practice for approved groups,
  assign activities, review student completion, and compare later reassessment
  results with earlier evidence.
- **Quiz authoring:** Create quizzes in the UI or import a CSV template, review and
  publish them, then inspect student attempts and misconception summaries. Students
  can explain their reasoning and try a teacher-authored repair question.
- **Lesson Studio:** Generate or edit structured lesson drafts, review learning
  objectives, explanations and answer keys, save revisions, approve and publish
  content, and attach published lessons to matching approved activities.
- **Learning evidence:** Inspect saved learning events, evidence summaries,
  recommendations, and teacher corrections to a diagnosis. Corrections are kept as
  an audit trail and do not rewrite the original model output.
- **Teacher copilot:** Ask for classroom-grounded summaries and suggestions. The
  copilot is advisory and cannot approve groups, publish lessons, or change grades.

## Student experience

- Choose a class and complete its assessment, including written reasoning.
- View available quizzes, submit responses, and discuss reasoning with bounded
  feedback. Correct answers and grading keys remain server-side.
- Open an assigned intervention, work through practice, request progressively
  specific hints, and complete an independent reassessment when eligible.
- View personal progress and saved learning evidence.
- Use the Learning Lab to download supported lessons and assigned practice for
  later use. Practice answers can be queued on the device and synchronized when
  the connection returns.

Offline support covers previously downloaded static learning content and queued
practice responses. New AI requests, protected reassessments, teacher approvals, and
other server-backed actions require connectivity.

## Learning and AI workflow

1. The student submits an answer and explanation; the backend stores the attempt.
2. Diagnosis uses the question, answer, explanation, and subject/topic taxonomy.
   Structured results are checked against known categories and supporting evidence.
3. The backend records learning events and updates an explainable, heuristic
   learner-state projection and a bounded next-action recommendation.
4. A teacher reviews diagnosis and proposed group membership, then explicitly
   approves a group before creating an assignment.
5. A teacher can prepare and review a lesson. Student practice and hints are tied
   to an approved assignment; completion gates reassessment.
6. The backend scores reassessment against its saved key and records the result as
   new evidence for progress reporting.

The app supports configured Gemini and OpenRouter providers, plus an explicit
mock/template path for offline demonstrations. Provider identity is surfaced so
template output is not presented as live AI. AI can propose text or a diagnosis; it
does not grade answers, approve teaching actions, or write arbitrary database
changes. Teacher-authored answer keys determine scores. Tutor feedback is
provisional and is not counted as independent mastery evidence.

## Demo content

The shared demo database has six synthetic subject/topic classes:

| Subject | Topics |
|---|---|
| Mathematics | Fractions; Basic algebra |
| Science | Force and motion; Basic electricity |
| English | Grammar; Subject-verb agreement |

The fractions class has 40 synthetic demo learners; each of the other five classes
has six. These records are generated examples, not real student data or evidence of
diagnostic accuracy. The app's class model scopes each class to one subject/topic;
the demo therefore represents cross-subject learning with separate class contexts,
not a single unified student roster.

## Technical implementation

- **Frontend:** React 19, Vite, React Router, Axios, and Recharts.
- **Backend:** Python FastAPI, SQLAlchemy, Pydantic, and Alembic migrations.
- **Storage:** PostgreSQL for the shared Compose setup; SQLite is also supported for
  isolated demos and tests.
- **Delivery:** Same-origin `/api` requests are proxied to the backend. The local
  share link was provided by a temporary Cloudflare Quick Tunnel.
- **Language and interaction:** English, Hindi, and Telugu interface resources,
  responsive layouts, keyboard and focus affordances, reduced-motion handling, and
  a static-shell PWA service worker.
- **Access controls:** Optional credential-backed sessions include role and class
  checks, session expiry/revocation, CSRF protection, and student-scoped access.
  Development demo identity is available only in development/test mode and is not
  production authentication.

## Scope and limitations

- The learner model uses bounded, explainable heuristics; it is not a validated
  psychometric measure or a fully adaptive question-selection engine.
- Independent educator-labeled accuracy, calibration, broad language-quality
  evaluation, and causal learning-gain studies have not been completed.
- The demo records are synthetic; the app is not evidence that the system improves
  student outcomes.
- The offline store uses browser storage that is not encrypted at rest and may be
  cleared by the browser. Background synchronization and a complete conflict
  resolution/export interface are not implemented.
- Production deployment still needs operational controls such as managed secrets,
  backups and recovery, retention/deletion policy, monitoring, a hardened reverse
  proxy and security headers, distributed rate limiting, account recovery, and an
  independent security review.
- Voice interaction, guardian summaries, and printable learning packs are outside
  this build.

## Further project documentation

- [Demo walkthrough](docs/DEMO_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API inventory](docs/API_INVENTORY.md)
- [Quiz workflow](docs/quiz_learning_loop.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [Implementation evidence and verification scope](docs/FINAL_IMPLEMENTATION_REPORT.md)
