# Implemented privacy and safety boundaries

AUTH_MODE=demo is only allowed with APP_ENV=development or test. It preserves the
explicit local synthetic-role workflow and is **not secure authentication**. Any
shared deployment must use AUTH_MODE=required. Settings reject demo mode in other
environments. Never expose a development/demo server containing real learners.

Credential mode uses privately provisioned teacher/student accounts, salted PBKDF2
SHA-256 password hashes, opaque random HttpOnly SameSite=Strict cookies, eight-hour
sessions by default, hashed session tokens in the database, server-side expiry and
logout revocation. Secure cookies are used outside development/test. Mutations
require the per-session CSRF header. Passwords are neither returned nor logged.
No public signup, password reset, or school identity provider is implemented.

A global API dependency checks roles and every referenced class/student/group/
assignment/reassessment/quiz/lesson. Credentials override forged demo headers;
student identities are derived from the session. Teacher ownership follows the
existing Class.teacher_id relationship. Student routes expose their own records;
teacher-only diagnosis, grouping, correction, lesson review and publication reject
students. Required mode disables demo roster/student-code identity resolution.
Class listings are filtered to the verified actor's authorized classes.

Teacher lesson review and publication also check scope in the service layer.
Group review records an exact membership fingerprint. Student tutor requests are
limited to owned approved assignments. Responses omit protected assessment keys.
Structured provider output is schema/taxonomy/evidence validated. A model has no
mutation tools, access to arbitrary SQL, or authority to approve teaching actions.

Diagnosis sends only the active question, rubric, answer, explanation and taxonomy.
Lesson generation sends deidentified aggregate evidence, subject/topic and target
concept, excluding student identifiers and evidence record IDs. Copilot provider
grounding now omits class name, student codes, named attention lists and raw sample
quotes; the authorized teacher's local context response still contains its records.
Teacher-entered chat and learner free text may themselves contain identifying text:
there is no guarantee of automated PII detection or vendor data-residency compliance.
Review provider policies and obtain school authorization before real-data use.

API responses use no-store. The service worker excludes /api and /health; it caches
only a static shell. Explicit downloads and queued responses are stored in
student-scoped IndexedDB on the device. They are not encrypted at rest. Logout
refuses silent loss of unsynchronized answers and clears local packages after
successful synchronization and logout. A user who retains physical/browser access
to an active session may access that student's local content. Browser storage
clearing and eviction can lose local data; shared phones require operational care.

Inference/login requests have bounded in-process rate controls. Production needs
HTTPS, a same-origin reverse proxy, secret management, backups, audited retention,
distributed rate limits for multiple workers, CSP/security policy, monitoring,
account recovery and independent security review. Audit/evidence records are retained
indefinitely by this MVP; no automated retention or deletion policy is implemented.
Raw provider response archives and hidden reasoning are not persisted. This is not
a claim of HIPAA/GDPR compliance or production-grade child-safety certification.
