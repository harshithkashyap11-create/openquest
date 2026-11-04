# Supported misconception taxonomy

Canonical definitions and descriptions are in `backend/app/subject_taxonomy.py`;
existing detailed material remains in `docs/misconception_taxonomy.md`.

| Subject/topic | Supported identifiers |
|---|---|
| Mathematics / Fractions | M01 additive numerator/denominator error; M02 whole-number comparison bias; M03 common denominator; M04 equivalence; M05 arithmetic slip; M06 insufficient evidence |
| Mathematics / Basic algebra | ALG01 inverse operation; ALG02 distribution; ALG03 variable operations |
| Science / Force and motion | FM01 continuous force belief; FM02 speed relationship; FM03 force/acceleration |
| Science / Basic electricity | EL01 open circuit; EL02 consumed current; EL03 electrical quantities |
| English / Grammar | GR01 tense; GR02 pronouns; GR03 capitalization/punctuation |
| English / Subject-verb agreement | SV01 intervening noun; SV02 number agreement; SV03 compound subject |

CORRECT and FOLLOW_UP are shared outcomes. M06 is the legacy fractions abstention.
A valid global code is still rejected if it does not belong to the active question
subject/topic. A misconception needs a nonempty verbatim evidence excerpt from the
actual answer or explanation. Unsupported labels and fabricated excerpts do not
enter the diagnosis ledger. Low or explicitly uncertain evidence requests follow-up
and is excluded from supported grouping and scored mastery.

The taxonomy is currently repository-versioned rather than a separate database
revision. Provider scores are uncalibrated; the UI uses qualitative uncertainty and
a caution. Teacher correction appends reason, actor, version and request identity,
preserves original model output, updates learner projection and future proposed
groups. The grouping service still chooses one primary misconception per student;
full multilabel grouping is an explicit limitation.
