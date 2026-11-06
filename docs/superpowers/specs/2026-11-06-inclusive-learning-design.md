# Inclusive Learning for ClassPulse — Design

**Status:** Proposed; awaiting product-owner approval  
**Date:** 2026-11-06  
**Product:** ClassPulse AI in `openpost`  
**Scope of this work:** Design only. No product code is authorized by this document. The working tree already contains uncommitted changes, including Inclusive Learning-related files; those changes were found before this document was written and have not been edited or treated as approved implementation.

## Intent

Give teachers a dedicated ClassPulse workspace for adapting an existing lesson to supports they select, reviewing the changes and verification evidence, and assigning an approved version. Students get an accessible reader and teacher-reviewed practice for lessons actually assigned to them.

The feature brings AccessBridge's source-aware adaptation and verification workflow into ClassPulse. It should use ClassPulse's existing classes, accounts, authorization, AI provider settings, lesson review conventions, database and migrations rather than becoming a second application. Support selections are instructional choices made by the teacher; no diagnosis or automated learner profiling is required.

## Goals

- Let an authorized teacher adapt either a saved ClassPulse lesson revision or an imported TXT, Markdown, DOCX, or text-based PDF lesson.
- Let a teacher select individual supports, optionally starting from AccessBridge's Reading, Attention, or Screen-reader presets. Presets are editable combinations of supports, not diagnoses or claims that a learner needs every item in them.
- Produce an English adaptation with traceable source-block references, objective mappings, support mappings, and teacher-facing verification.
- Let teachers edit, verify, review, approve, and assign a version; any educational-content edit invalidates that version's prior verification and approval.
- Assign approved versions to an individual student, an existing teacher-approved group, or the whole class, with recipients constrained to that class.
- Give each student an accessible lesson reader and assigned teacher-reviewed practice without exposing teacher reports, support selections, answer keys, or another student's work.
- Export a standalone HTML lesson, printable PDF, narration text/SSML, and a separate teacher-facing verification report. Mark unapproved exports as drafts.

## Non-goals and anti-goals

- Creating a new lesson from only a topic or objectives. Release one adapts an existing source lesson.
- Inferring a diagnosis, disability, profile, or accommodation from student answers or behavior; selecting supports automatically; or requiring a diagnosis to use the feature.
- AI grading, autonomous approval/publication, autonomous assignment, or replacing teacher judgment.
- Claiming accessibility certification, legal compliance, educational effectiveness, or guaranteed suitability for an individual student.
- OCR, scanned/image-only PDF ingestion, or interpretation of source images.
- Adapting or verifying lesson content in Hindi or Telugu in release one. Existing ClassPulse interface locales remain available; adaptation and verification content are English-only.
- Sending student identities, rosters, class membership, or unrelated classroom evidence to the model.
- Showing a student's selected support configuration or teacher verification report in student APIs, exports, or UI.
- Running a second AccessBridge service/database alongside ClassPulse or introducing a general-purpose autonomous agent framework.

## Product flow

### Teacher workspace

Add **Inclusive Learning** to teacher navigation and scope every page and API operation to the selected ClassPulse class.

1. **Choose a source.** Select an existing lesson revision belonging to this class, or import a TXT, Markdown, DOCX, or text-based PDF file. The source is parsed into ordered, addressable blocks, preserving headings and PDF page references where available. Imported material is saved as a ClassPulse source record. A source chosen from Lesson Studio is snapshotted at the exact revision so later edits to the original cannot silently change an adaptation.
2. **Choose supports.** The teacher may select individual support items or apply one or more editable starting presets: Reading, Attention, Screen-reader. The choices apply to this adaptation, not to the student's account or permanent learner record. No diagnosis is requested. The teacher may adapt for the whole class without selecting a student first.
3. **Adapt.** A bounded, typed AI workflow analyzes source objectives and blocks, creates a draft for the selected supports, then runs verification. Each generated block carries valid source-block, objective, and support references. Provider/model provenance, request failure, and retry state are explicit. A failed stage leaves the saved source and prior versions intact; it must not return a success-shaped empty draft or silently label a template as live AI.
4. **Review side by side.** Show source and adapted blocks together. For each changed block, show the original source references, objective/support mappings, change explanation, verification findings and verbatim evidence where supplied. Show objective coverage, deterministic checks, semantic checks, unresolved findings, and the limitations of each check. Findings remain visible after teacher decisions; teacher acknowledgment never rewrites an AI result.
5. **Edit, re-verify, approve.** Teachers can edit adapted content and review practice/answer keys. Saving a content edit creates a new immutable adaptation version and clears approval/current verification. Re-verification always targets the exact current version. Approval records the teacher, version, time and review note. A finding can be acknowledged with an explicit reason; acknowledgment is not a PASS and does not change the report. Invalid source references, invalid block structure, or detected answer-key exposure are hard blockers. Other unresolved findings require explicit teacher acknowledgment and remain visible.
6. **Assign.** Assign only an approved adaptation version. Choose one student, a teacher-approved group from this same class, or the entire class. Resolve the audience server-side and snapshot the exact recipients at assignment time. A later group membership change must not add recipients to an existing assignment. There is no per-assignment teacher revoke action in release one; assignments remain in history. Current class membership and student ownership remain mandatory for access, so leaving the class ends access even though the assignment record is retained. Retries are idempotent and do not duplicate assignments.

### Student learning area

Add **My Inclusive Learning** to student navigation. List only current, assigned adaptations for the authenticated student. Each assignment is pinned to the approved version; publishing a later version does not silently alter work already assigned.

The lesson reader uses semantic headings, a predictable keyboard order, visible focus, appropriately labeled controls, and text rendered as text rather than HTML. Offer text-size and spacing controls and optional browser-native read-aloud; indicate when speech synthesis is unavailable. Controls alter presentation, not lesson content or teacher verification.

Practice is adapted from questions already present in the source lesson; release one does not ask AI to author additional questions. Teachers review the adapted questions and answer keys before approval. The student payload excludes keys, teacher notes, support selections, profile labels, verification reports, internal source identifiers, and other students' records. The server grades with the stored teacher key, never the model; feedback uses teacher-reviewed explanations/hints. Record completion and responses in ClassPulse without assigning a mastery or diagnostic label.

## AccessBridge reuse and ClassPulse integration

Port AccessBridge's typed domain concepts and service logic into the existing FastAPI backend; do not call its local app, SQLite store, or HTTP server at runtime. Reuse the ClassPulse configured Gemini/OpenRouter provider boundary and the current teacher/student identity, class scoping, CSRF, migration, and lesson review patterns.

The three bounded stages are:

1. **Analysis:** identify source-supported objectives, key concepts/vocabulary, relevant source blocks, and a plan for each selected support.
2. **Transformation:** produce a complete English adaptation with per-block source/objective/support mappings and a concise change rationale.
3. **Verification:** combine deterministic checks with structured semantic checks. Validate every model-supplied ID against the saved source, objective catalog, selected supports, and current adaptation version. Accept a PASS quotation only if it is an exact quote from the cited adapted block. Missing, duplicate, invented, or ungrounded findings become unresolved review findings.

Provider output is untrusted data. Do not execute generated markup, instructions, SQL, or tools. Prompts must distinguish source lesson text from instructions. Use the existing provider timeout/rate limits and surface provider/configuration errors without exposing credentials or raw provider bodies.

Support definitions should come from a versioned server-side catalog based on AccessBridge's current Reading, Attention, and Screen-reader presets. The preset list is not a fixed learner model: teachers can choose individual support items, edit a preset selection before generating, and record only the supports used for that adaptation.

## Data and version lifecycle

Persist in ClassPulse's existing SQLAlchemy database with additive Alembic migrations. Use relational ownership/foreign-key fields for class, source, adaptation, revision, review, assignment, student and practice records; structured JSON may hold validated block content and verification details. Keep source records, adaptation versions, reports, and reviews separately addressable.

Each verification report is immutable and bound to `(adaptation_id, adaptation_version, source_version, support_catalog_version)`. Each approval is bound to the exact adaptation version and its current report. An edit creates a new version, leaves historical reports/reviews available to teachers, and makes all previous reports and approval stale for current use. Assignment records reference the exact approved revision and snapshot resolved recipients. Assignments are not manually revocable in release one, but every read still checks that the authenticated student remains a member of the owning class. Practice attempts reference the assignment and student and are idempotent for a stable request identity.

Do not make support choices part of ClassPulse's permanent learner state. Student-facing serializers must be allowlists, not full-model serialization with a blacklist. Source files are size-limited, parsed locally, and persisted only according to existing ClassPulse storage conventions; provider calls receive only the lesson content and support instructions needed for that operation. Follow current ClassPulse retention behavior: this feature adds no automated deletion or teacher deletion controls, and source, adaptation, report, assignment, and practice records remain subject to the existing retention policy.

## API shape

Final names should follow local route/schema conventions, but the capability surface should cover:

- Teacher: list support catalog; list/create/import sources; select/snapshot a ClassPulse lesson revision; list sources; create/list adaptations; edit a current adaptation; verify/re-verify; approve; assign to one student, approved group, or class; download each export/report.
- Student: list assigned lessons; fetch one assignment's student-safe content; submit assigned practice; fetch own completion/status.
- All teacher endpoints take an explicit class context and enforce class ownership. Student endpoints derive identity from the authenticated account and enforce assignment ownership. In demo mode, preserve the repository's existing explicit local-demo boundary and do not describe it as production authentication.
- A request for any adaptation, source, report, revision, or assignment outside the caller's class/ownership returns a non-disclosing authorization/not-found response.

## Exports

- **HTML:** standalone, semantic, keyboard readable, safely escaped; contains only student-safe lesson content and an explicit `DRAFT — NOT APPROVED` notice until the exported version has current approval.
- **PDF:** printable version of the same lesson content and status. Treat it as a print artifact; do not claim PDF/UA or screen-reader compliance without separate testing.
- **Narration:** generate TXT and valid SSML deterministically from the current ordered lesson blocks so exports cannot be stale relative to saved edits. Mark drafts clearly.
- **Teacher report:** separate download containing source/objective/support traceability, current and historical findings, evidence, review/approval record, model/provider provenance, and explicit limitations. Never bundle it into a student export.

Exports must be generated from server-fetched records, not client-supplied approval status or content. Draft exports remain available to teachers but never appear in student assignment lists.

## Accessibility, privacy, and safety

Use the frontend accessibility skill's semantic, keyboard, focus, and labeling patterns. Validate controls with keyboard-only tests and automated accessibility checks; manual screen-reader testing remains necessary. Browser read-aloud is optional and device-dependent.

Lesson content is sent to the configured third-party provider when live adaptation or semantic verification is requested. Teachers must be warned not to submit confidential identifying information. Do not include student IDs or support-recipient membership in prompts. Preserve provenance and data minimization; do not claim automated PII detection or provider residency. Treat imported lesson text as untrusted prompt data. No browser markup from the model is rendered directly.

Presets are examples of supports, not universal prescriptions for autistic, dyslexic, or other students. Use neutral teacher-facing language; do not label a student with a profile in student content. Verification is an aid for a teacher and does not certify accessibility, safety, factual correctness, or individualized suitability.

## Verification plan and acceptance criteria

### Backend/API

- Parse supported TXT, Markdown, DOCX, and text-based PDFs; reject unsupported, oversized, malformed, encrypted, empty, scanned/image-only, or non-English source content with actionable errors. Preserve source order and page/heading references where available.
- Verify source selection snapshots the exact ClassPulse lesson revision; later source edits do not mutate it.
- Test valid adaptation, provider failure at each stage, explicit retry, idempotency, invalid model IDs/references, missing/duplicate semantic checks, invalid evidence quotations, source/objective traceability, deterministic checks, unresolved findings, and exact-version report binding.
- Test that each content edit creates a new version and invalidates prior verification and approval; re-verification of that version is required before approval.
- Test approval acknowledgment, hard blockers, audit history, and that acknowledgment never changes check outcomes.
- Test assignment to one student, approved group, and class; reject foreign classes, unapproved groups, and out-of-class students; snapshot recipients and prevent duplicate assignment on retries.
- Test student endpoint ownership and payload minimization, including hidden support selections, teacher reports, keys, review notes and unrelated students.
- Test deterministic practice grading, no AI grading, completion persistence, and attempt idempotency.
- Test HTML/PDF/narration/report outputs, draft labels, approved labels, no secrets or teacher-only fields in student formats, and no active HTML execution.
- Run migrations against SQLite and verify generated PostgreSQL DDL; execute PostgreSQL migration/integration tests when a disposable PostgreSQL database is available.

### Frontend

- Cover the complete teacher journey: choose/import source → choose supports → generate → inspect report → edit → re-verify → approve → assign.
- Cover the student journey: view assigned lesson → adjust reading controls → optionally read aloud → submit practice → receive teacher-authored feedback → completion.
- Check keyboard-only navigation, focus visibility/order, screen-reader semantics/labels, responsive layout, and unavailable speech-synthesis behavior.
- Confirm student UI never shows teacher report/support selection and only assigned approved lesson versions are rendered.

### Evidence/limits

Tests establish software behavior, not that supports work for a specific student. A pilot needs educator and learner feedback, specialist review where appropriate, and independent evaluation. Report model/provider, version, checks, unresolved count, latency and cost only when measured; do not claim learning gains from completion alone.

## Open implementation choices for the builder

- Choose normalized table boundaries and route/schema names that best fit current ClassPulse conventions while preserving the lifecycle and authorization guarantees above.
- Choose accessible component layout and concise copy consistent with the existing ClassPulse design system.
- Choose exact upload limits, supported DOCX/PDF parsing details, migration indexes, pagination, and provider timeout handling based on existing repo patterns; document the selected values.
- Keep all exported and API content validated and version-bound; do not relax hard safety or ownership requirements for demo convenience.
