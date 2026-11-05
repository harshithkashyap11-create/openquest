# Initial Database Design

The Alembic migration history is the sole schema authority. `backend/schema.sql` is generated from Alembic offline SQL and must not be edited independently.

## Tables
- `teachers`: teacher accounts.
- `classes`: class groups owned by teachers.
- `students`: pseudonymous learner records in a class.
- `questions`: assessment questions and topic metadata.
- `submissions`: learner answers and explanations.
- `diagnoses`: provisional AI/teacher labels, confidence and evidence.
- `learning_groups`: teacher-reviewed groups for a class/topic.
- `group_members`: membership history.
- `interventions`: reusable corrective activities.
- `intervention_assignments`: activity assignments and completion.
- `reassessment_results`: later evidence of learning.

## Important relationships
- One teacher has many classes.
- One class has many students.
- One question has many submissions.
- One submission can have multiple diagnosis records over time.
- One learning group has many students through `group_members`.
- One intervention can be assigned to many students.
- Reassessment results link a student, question and intervention assignment.

## Implementation notes
Use UUID primary keys, UTC timestamps, foreign keys and database constraints.
Keep `expected_label` in the offline synthetic ground-truth file only; do not expose it to the diagnosis service.
Store diagnosis evidence and model/prompt version for auditability.

`submissions` enforces `UNIQUE (student_id, question_id)` in the database for the current one-response-per-question dataset. Supporting multiple attempts requires a deliberate schema change, such as an `attempt_no` column and revised uniqueness constraint.


## Map and journey read models (2026-11-05)

No schema migration is required; Alembic head remains 0007_learning_intelligence.
Map queries read existing submissions, questions, students, diagnoses and
versioned diagnosis_corrections. Attention additionally reads group review_status,
assignment status and reassessment status. The journey reads submissions,
intervention_assignments, practice_responses and reassessments; its IDs identify
those source rows. Assignments link to reassessments through assignment_id. No
response-to-assignment link or teacher review history is invented. Corrections
continue to append to diagnosis_corrections; original diagnosis fields are intact.
The evaluation manifest and aggregate status report are local files, not classroom
tables. Demo isolation is a fresh, exclusive SQLite path; an application marker
never grants permission to delete records from a mixed database.
