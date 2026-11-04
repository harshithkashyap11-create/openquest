# Evaluation integrity

The original `data/ground_truth.json` and synthetic CSV fixtures are development
regression material. They are not independent school outcomes. Existing mock
heuristics must never be evaluated against their own generated labels as though
that measured real-world diagnostic accuracy.

`backend/scripts/probe_ai.py --live` makes four bounded synthetic inference calls:
two Mathematics reasoning cases, one Science and one English case. It checks
transport, structured parsing, taxonomy compatibility and verbatim evidence. It
records per-case wall-clock latency and the configured/reported model. **Four smoke
cases do not establish accuracy, generalization or learning impact.**

`verify_live_lessons.py --live` generates three synthetic M01 drafts (en/hi/te) in
an isolated database. It exercises the actual generation API and structured schema.
The supplied samples were inspected for targeted fraction addition and arithmetic.
Human language adjudication and broad subject coverage remain NOT TESTED.

For independent evaluation, separate development and held-out items by underlying
question, scenario and explanation—not just row ID. Use at least two reviewers
where feasible, label misconception, correctness, ambiguity and insufficient
evidence separately, and document disagreements and adjudication. Exclude examples
used in prompts or tuning. Record language, subject/topic, dataset provenance,
reviewer, review status, taxonomy/prompt/model version and excluded rows. Do not
invent reviewer identities or independent labels.

`evaluation_metrics.py` accepts JSON rows with subject, expected, predicted,
review_status and reviewer. Its CLI refuses independent evaluation without
adjudicated references. `--allow-synthetic-regression` explicitly labels a synthetic
regression run. Unit tests validate accounting with known small examples.

Precision = TP/(TP+FP); recall = TP/(TP+FN); F1 = 2PR/(P+R), zero division = 0.
Macro-F1 averages over expected reference labels. Confusion matrices retain
abstentions and unsupported predictions. Abstention rate counts M06/FOLLOW_UP;
unsupported-output rate counts predictions outside the canonical taxonomy. Report
sample counts and per-subject coverage beside all scores. Separate transport,
schema-validation and educational abstention failures. No missing predictions
should be silently dropped from an independent evaluation denominator.

Provider latency measurements use monotonic wall time including request overhead;
there is no automatic retry in the smoke runner. Failed/time-out attempts stay in
the report. The sample is too small for reliable tail latency or throughput claims.
Real Android/network-throttled performance, calibration and longitudinal learning
improvement are NOT TESTED. No causal learning-impact claim is supported.
