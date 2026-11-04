# Guided tutoring and assessment integrity

The new tutor is bound to an existing approved intervention assignment. It accepts
an assignment identifier and practice-question index, never a diagnostic or
reassessment question identifier. Ownership, assignment status and question range
are enforced on the server. It closes when the activity is completed and an
independent reassessment becomes available.

The four levels are: conceptual attention; applicable relationship/procedure;
question-specific next step; an analogous worked example leaving the current
question for the learner. A response is required between consumed levels. After
level four, the learner is directed to try practice or contact a teacher. History
survives reload and retries do not consume another level.

The default hints are **deterministic misconception-specific templates**. A learner
can explicitly select live response-aware guidance through the configured provider.
The live path receives the active question, target concept, prior hints, level and
actual response, without learner identifiers or an answer key. It validates a
structured hint, provisional correct/partial/incorrect/uncertain feedback and a
verbatim evidence excerpt. Numeric-equivalence and exact-phrase guards reject final
answer disclosures; failures do not consume a hint. A rejected or unavailable live
response returns 503 and the learner can explicitly select labeled templates.
No filter guarantees detection of every possible paraphrased answer; protected
assessments remain structurally inaccessible to this tutor. English ladders use the existing verified templates for all supported codes.
Hindi/Telugu ladders currently support M01. Unsupported regional hint requests fail
explicitly; they do not silently switch language. Approved published lessons can
be attached to matching existing assignments and shown in the tutoring context.

Practice correctness is checked against stored keys and saved separately from
independent reassessment. All practice questions must have persisted responses
before completion; correctness is not required to access the independent check.
The evidence policy then recommends an appropriate difficulty and follow-up action.
A single correct answer or hint request does not establish secure mastery.

Protected assessment keys are absent from student assessment responses. Student
lesson practice keys are omitted, while analogous worked examples remain visible.
Hints cannot be requested for reassessment items through this API. The existing
quiz reflection tutor remains a separate post-submission format and is preserved.

Limitations: live feedback is provisional and does not add independent mastery
credit. Actual adaptive question-bank selection, robust affect-aware safety handling
and independently evaluated multilingual tutoring remain incomplete. The product must not imply those
capabilities from the presence of a tutor screen.
