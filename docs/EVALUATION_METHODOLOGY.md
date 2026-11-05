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


## Held-out report and baseline command (2026-11-05)

Current status: **NOT TESTED**. `evaluation-status.json` records dataset size 0,
educator-labeled count 0, held-out count 0, and null metrics. No reviewer identities
or human labels have been invented. Existing synthetic CSVs were used for prior
engineering development and must not be relabeled as independent held-out data.

From `backend`, inspect readiness without touching a database or provider:

```bash
python -m scripts.heldout_evaluation
```

An educator/maintainer can prepare an approved local JSON manifest. Do not commit
private student text. The required structure is:

```json
{
  "dataset_version": "approved-local-version",
  "taxonomy_version": "repository-taxonomy-version",
  "model_id": "recorded-provider-and-model",
  "prompt_version": "recorded-prompt-version",
  "split_method": "source-group assignment before tuning",
  "split_seed": 17,
  "records": []
}
```

The empty list above is a format illustration and is deliberately rejected as an
evaluation dataset. Each record must have `id`, `source_group`, `split`
(`development` or `held_out`), `subject`, `topic`, `language` (`en`, `hi`, `te`),
`provenance` (`educator_authored`, `deidentified` or `synthetic`), `response`,
`expected`, `review_status` (`adjudicated`), `reviewer_id`, `reviewer_role`
(`educator`), timezone-aware `reviewed_at`, `used_for_tuning`, and `prediction`.
The prediction contains `status` (`valid`, `uncertain`, `invalid`,
`provider_failed`, `missing`) and `code`. Valid codes must belong to that topic;
uncertain outputs use M06/FOLLOW_UP; failed/invalid/missing outputs use null code.
References require concrete taxonomy labels or CORRECT; ambiguous/insufficient
reference cases need a separate adjudication study, not this classifier report.
Labels and metadata must be supplied by actual reviewers; setting these fields is
not evidence that a human review happened. Prefer independent double annotation
and documented adjudication. Group related question/scenario variants under the
same source_group. The code rejects cross-split groups, duplicate IDs, unsupported
labels, missing review fields and held-out records marked used_for_tuning. It
cannot independently detect past prompt exposure or dishonest provenance.

Freeze the grouping, split and prompt before scoring. The recorded seed describes
the source split; this tool does not reshuffle or tune data. Use a majority-label
baseline learned only from development labels (lexical tie break). It predicts
that fixed label for every held-out item, using no privileged item information.
It is intentionally simple and does not model subject-specific reasoning.

```bash
python -m scripts.heldout_evaluation --input /absolute/private/approved.json --output /tmp/new-evaluation-report.json
```

An existing report path is refused. A synthetic-only accounting check requires
`--allow-synthetic-regression` and is labeled SYNTHETIC_REGRESSION_ONLY. Mixed
provenance must be evaluated separately. Neither command uploads data or calls an
LLM. Reports omit raw responses and individual record/reviewer identifiers and
include a dataset digest, dataset/model/prompt/taxonomy versions, run timestamp,
split method/seed, sample sizes and language counts. Keep private manifests local.

Metrics are defined before computation: exact-label matches divided by **all**
held-out records; per-label precision/recall/F1 (zero division=0); macro-F1 over
expected labels. Abstentions, malformed/missing outputs and provider failures
remain in the denominator and confusion matrix. Outcome counts distinguish valid,
uncertain, invalid, missing and provider-failed output. Model and baseline use the
same held-out items globally and by subject. Report support beside every score;
small slices are descriptive only. No statistical significance, calibration,
classroom accuracy or causal educational-effect claim follows from this report.
