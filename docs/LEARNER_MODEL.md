# Persistent learner model

`learning_events` is the append-only application evidence ledger. Each record has
student, subject, topic, event kind, unique source key, structured data and server
time. There is no public arbitrary-event writer. The original submissions and
model diagnoses remain authoritative source records. Corrections append records;
they do not rewrite model output.

`learner_states` stores a unique student/subject/topic projection with an optimistic
version. `learning_sessions` stores the corresponding workflow state/version.
`learning_decisions` stores one allowlisted decision per accepted event with its
supporting event, reason, approval requirement, source and `evidence-v1` policy.
`mutation_receipts` makes selected mobile mutations replayable in the same database
transaction. Unique keys and optimistic updates return 409 on conflicting writes.
SQLite connections enforce foreign keys and a five-second busy timeout.

The projection uses up to ten recent independently scored diagnosis/reassessment
observations. Assisted practice and hints do not add mastery credit. Diagnoses
marked uncertain are excluded from scored mastery evidence. Correctness is checked
against the question key separately from the misconception classification. A
correct answer with flawed reasoning can therefore retain a learning gap.

- Score: correct scored observations / scored observations × 100; an **uncalibrated
  heuristic**, never a scientific probability.
- Secure: at least three scored observations across at least two attempts, recent
  score at least 80, and no active supported gap.
- Developing: some scored evidence and score at least 50; otherwise needs support.
  Without scored evidence, status is insufficient evidence.
- Difficulty recommendation: challenging for secure; foundation after at least
  three recent observations with score below 40; standard otherwise.
- A supported gap remains until corrected or three later targeted reassessment
  responses are correct. Its historical evidence is retained.
- Hint count comes from unique delivered hint requests, never generated content.

One repeated source key with identical data returns the original event without a
second projection update. Reusing it for different data conflicts. A correction
replaces the judgement for its original observation identifier in replay; a later
unrelated response cannot replace that correction.

`project(events)` is a pure deterministic replay function. New transactions rebuild
the topic projection from the ledger. Historical pre-upgrade diagnoses are not
silently backfilled into the live database. The isolated demo explicitly creates
its labeled fixture evidence; new live workflow events update state automatically.
A production backfill/reconciliation command and incremental projection optimization
remain future work. Current evidence views are intended for hackathon class sizes.

No score is evidence of causal educational benefit. Question-bank equivalence,
long-term retention, calibrated mastery and adaptive question selection have not
been established. Difficulty is a recommendation; the reassessment catalog remains
the existing verified topic-specific bank.
