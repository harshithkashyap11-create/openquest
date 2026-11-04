# Frontend route-to-API evidence map

All API calls use centralized Axios configuration and same-origin Vite proxy. In
credential mode the server session controls identity, regardless of demo headers.
Errors expose retry controls or preserve draft/queued data; they do not claim success.

| Route/action | API / data dependency | Failure behavior |
|---|---|---|
| /login local demo | /auth/config, /demo/classes, /demo/students/resolve | Explicit self-asserted synthetic identity, retryable catalog errors |
| /login verified accounts | /auth/login; provisioned accounts/sessions | Invalid credentials 401; CSRF/session checks; no demo student-code login |
| /student/assessment | class assessment and student assessment-submissions | Stores attempt before AI; pending retry key prevents duplicates |
| /teacher/overview | assessment/diagnosis summaries; bounded diagnose command | Request lifecycle and provider errors; saved submissions remain |
| /teacher/insights | class diagnoses and summary | Evidence, qualitative uncertainty, original provider/model; correction workflow separately accessible |
| /teacher/interventions | groups/generate, group/review, intervention/generate | Scope/revision/approval guards, truthful template provenance |
| /student/interventions | own assignments, submit/complete, reassessment/submit | Server eligibility and ownership, completed-result retry is idempotent |
| /teacher/learning | class learning-states, diagnoses, taxonomy, corrections | Stored ledger and source records; no placeholder learner percentages |
| /teacher/lessons | class lessons/generate, lesson edit/review/assign | Structured draft, optimistic revisions, explicit review/publication and private keys |
| /student/learning | own learning-state, published lessons, assignments, tutor/hints, sync-practice | Four-level hint bound, downloaded-content fallback, retained sync conflicts |
| /teacher/progress and /student/progress | progress_service over baseline/reassessment/assignments | Real sample counts and empty states; no causal learning claim |
| Teacher Copilot sidebar | /copilot/chat and read-only context | Provider/fallback labels; class scoped and deidentified provider grounding |
| Teacher/student quiz routes | Existing quiz APIs and quiz/reflection persistence | Preserved original learning-loop behavior and browser coverage |

The existing sage/cream visual identity, shared panel/button styles, role layout,
responsive navigation, reduced-motion controls and language selector were reused.
New interactive controls have connected labels, keyboard-native elements, visible
focus, touch-sized actions, semantic headings and announced dynamic messages.
