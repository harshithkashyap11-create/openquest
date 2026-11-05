"""Offline held-out evaluation. Never contacts a provider or opens classroom data."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.subject_taxonomy import get_taxonomy


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Prediction(StrictRecord):
    status: Literal['valid', 'uncertain', 'invalid', 'provider_failed', 'missing']
    code: str | None = Field(default=None, max_length=40)


class LabeledRecord(StrictRecord):
    id: str = Field(min_length=1, max_length=100)
    source_group: str = Field(min_length=1, max_length=100)
    split: Literal['development', 'held_out']
    subject: str
    topic: str
    language: Literal['en', 'hi', 'te']
    provenance: Literal['synthetic', 'educator_authored', 'deidentified']
    response: str = Field(min_length=1, max_length=10000)
    expected: str
    review_status: Literal['adjudicated']
    reviewer_id: str = Field(min_length=1, max_length=100)
    reviewer_role: Literal['educator']
    reviewed_at: datetime
    used_for_tuning: bool
    prediction: Prediction

    @model_validator(mode='after')
    def validate_labels(self):
        supported = {item.code for item in get_taxonomy(self.subject, self.topic)} | {'CORRECT'}
        if self.expected not in supported or self.expected in {'M06', 'FOLLOW_UP'}:
            raise ValueError('Reference requires a supported, non-abstention label')
        if self.reviewed_at.tzinfo is None:
            raise ValueError('Review timestamp requires a timezone')
        prediction = self.prediction
        if prediction.status == 'valid' and (prediction.code not in supported or prediction.code == 'M06'):
            raise ValueError('Valid predictions require a supported label')
        if prediction.status == 'uncertain' and prediction.code not in {'M06', 'FOLLOW_UP'}:
            raise ValueError('Uncertain outputs require an explicit abstention code')
        if prediction.status in {'invalid', 'provider_failed', 'missing'} and prediction.code is not None:
            raise ValueError('Failed outputs must not carry a usable prediction')
        if self.split == 'held_out' and self.used_for_tuning:
            raise ValueError('Held-out records must not have been used for tuning')
        return self


class Dataset(StrictRecord):
    dataset_version: str = Field(min_length=1, max_length=100)
    taxonomy_version: str = Field(min_length=1, max_length=100)
    model_id: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)
    split_method: str = Field(min_length=1, max_length=200)
    split_seed: int
    records: list[LabeledRecord] = Field(min_length=2, max_length=10000)


def classification(rows: list[LabeledRecord], predictions: list[str | None]) -> dict:
    """All held-out rows remain in denominators, including missing/failed outputs."""
    labels = sorted({row.expected for row in rows})
    per_label = {}
    confusion = {}
    for label in labels:
        true_positive = sum(row.expected == label and predicted == label for row, predicted in zip(rows, predictions))
        predicted_count = predictions.count(label)
        support = sum(row.expected == label for row in rows)
        precision = true_positive / predicted_count if predicted_count else 0
        recall = true_positive / support
        per_label[label] = dict(support=support, precision=precision, recall=recall,
            f1=2 * precision * recall / (precision + recall) if precision + recall else 0)
        confusion[label] = dict(sorted(Counter(
            predicted or f'[{row.prediction.status}]'
            for row, predicted in zip(rows, predictions) if row.expected == label).items()))
    correct = sum(row.expected == predicted for row, predicted in zip(rows, predictions))
    return dict(sample_count=len(rows), correct=correct, accuracy=correct / len(rows), per_label=per_label,
        macro_f1=sum(item['f1'] for item in per_label.values()) / len(labels), confusion_matrix=confusion)


def evaluate(data: dict, *, allow_synthetic: bool = False) -> dict:
    try:
        dataset = Dataset.model_validate(data)
    except (ValidationError, ValueError) as error:
        # Pydantic's raw errors include input values; do not echo student text.
        raise ValueError('Invalid evaluation schema, labels, review metadata or prediction state; inspect the documented format locally.') from error
    rows = dataset.records
    if len({row.id for row in rows}) != len(rows):
        raise ValueError('Duplicate evaluation IDs')
    development = [row for row in rows if row.split == 'development']
    held_out = [row for row in rows if row.split == 'held_out']
    if not development or not held_out:
        raise ValueError('Both development and held-out source groups are required')
    if {row.source_group for row in development} & {row.source_group for row in held_out}:
        raise ValueError('Source groups overlap between development and held-out data')
    provenances = sorted({row.provenance for row in rows})
    if len(provenances) != 1:
        raise ValueError('Evaluate each provenance separately; do not mix synthetic and classroom sources')
    synthetic = provenances == ['synthetic']
    if synthetic and not allow_synthetic:
        raise ValueError('Independent evaluation NOT TESTED: synthetic data requires --allow-synthetic-regression')
    # Freeze the baseline from development references only. Ties are lexical.
    counts = Counter(row.expected for row in development)
    baseline_label = sorted(counts, key=lambda label: (-counts[label], label))[0]
    predictions = [row.prediction.code if row.prediction.status in {'valid', 'uncertain'} else None for row in held_out]
    model = classification(held_out, predictions)
    model['outcomes'] = {state: sum(row.prediction.status == state for row in held_out)
        for state in ['valid', 'uncertain', 'provider_failed', 'invalid', 'missing']}
    baseline = classification(held_out, [baseline_label] * len(held_out))
    baseline.update(label=baseline_label, rule='Majority development label; lexical tie break. Same held-out records as model.')
    subject_results = {}
    for subject in sorted({row.subject for row in held_out}):
        indexes = [i for i, row in enumerate(held_out) if row.subject == subject]
        subset = [held_out[i] for i in indexes]
        subject_results[subject] = dict(model=classification(subset, [predictions[i] for i in indexes]),
            baseline=classification(subset, [baseline_label] * len(subset)))
    digest = sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return dict(status='SYNTHETIC_REGRESSION_ONLY' if synthetic else 'RECORDED_EDUCATOR_REFERENCES',
        dataset_version=dataset.dataset_version, dataset_sha256=digest, run_id=digest[:16],
        model_id=dataset.model_id, prompt_version=dataset.prompt_version, taxonomy_version=dataset.taxonomy_version,
        split_method=dataset.split_method, split_seed=dataset.split_seed, provenance=provenances[0],
        total_count=len(rows), development_count=len(development), held_out_count=len(held_out),
        language_counts=dict(Counter(row.language for row in held_out)), model=model, baseline=baseline, by_subject=subject_results,
        definitions='Exact match over all held-out records. Abstentions, invalid, missing and provider-failed outputs remain in denominator. Precision/recall/F1 use zero division=0; macro-F1 averages expected labels.',
        limitations=['Recorded metadata does not independently verify reviewer identity or absence of prior exposure.',
            'Small samples and narrow source groups do not establish classroom performance, language quality, calibrated confidence or causal learning effects.',
            'Reference labels exclude ambiguous/insufficient-evidence cases; evaluate those separately. No tuning is performed by this script.'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Approved local JSON dataset; never uploaded')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-synthetic-regression', action='store_true')
    args = parser.parse_args()
    if args.input is None:
        report = dict(status='NOT_TESTED', dataset_size=0, educator_labeled_count=0, held_out_count=0,
            baseline='Majority label from development references, frozen before held-out scoring; not computed.',
            metrics=None, reason='No approved educator-labeled held-out dataset was supplied. Repository fixtures are engineering-authored synthetic development material.')
    else:
        try:
            report = evaluate(json.loads(args.input.read_text()), allow_synthetic=args.allow_synthetic_regression)
        except (ValueError, OSError):
            parser.exit(2, 'Evaluation rejected: invalid/unreadable data, unreviewed references, synthetic provenance without opt-in, or overlapping/tuned held-out groups. No metrics produced.\n')
    report['run_at'] = datetime.now(timezone.utc).isoformat()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        # Refuse overwrite of an existing report; runs remain inspectable.
        with args.output.open('x', encoding='utf-8') as destination:
            destination.write(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
