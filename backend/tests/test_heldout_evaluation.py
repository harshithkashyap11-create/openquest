"""Hand-counted offline comparisons; these records are test-only synthetic data."""
from copy import deepcopy
import pytest
from scripts.heldout_evaluation import evaluate


def dataset():
    rows = []
    for index, (split, expected, predicted, state) in enumerate([
        ('development', 'M01', 'M01', 'valid'),
        ('development', 'M01', 'M01', 'valid'),
        ('development', 'M02', 'M02', 'valid'),
        ('held_out', 'M01', 'M01', 'valid'),
        ('held_out', 'M02', 'M01', 'valid'),
        ('held_out', 'M02', 'FOLLOW_UP', 'uncertain'),
        ('held_out', 'M01', None, 'provider_failed'),
        ('held_out', 'M01', None, 'invalid'),
    ]):
        rows.append(dict(id=f'test-{index}', source_group=f'scenario-{index}', split=split,
            subject='Mathematics', topic='Fractions', language='en', provenance='synthetic',
            response='Synthetic test answer only', expected=expected,
            review_status='adjudicated', reviewer_id='test-only-reviewer', reviewer_role='educator',
            reviewed_at='2026-11-04T12:00:00Z', used_for_tuning=False,
            prediction=dict(status=state, code=predicted)))
    return dict(dataset_version='test-only-v1', taxonomy_version='repository-v1',
        model_id='recorded-test-only', prompt_version='test-only', split_method='source-group assignment', split_seed=17, records=rows)


def test_same_heldout_denominator_and_development_majority_baseline():
    report = evaluate(dataset(), allow_synthetic=True)
    assert report['status'] == 'SYNTHETIC_REGRESSION_ONLY'
    assert report['held_out_count'] == 5 and report['development_count'] == 3
    assert report['model']['correct'] == 1 and report['model']['accuracy'] == .2
    assert report['baseline']['correct'] == 3 and report['baseline']['accuracy'] == .6
    assert report['baseline']['label'] == 'M01'
    assert report['model']['outcomes'] == {'valid': 2, 'uncertain': 1, 'provider_failed': 1, 'invalid': 1, 'missing': 0}
    assert report['model']['per_label']['M01']['recall'] == pytest.approx(1/3)
    assert report['model']['per_label']['M02']['support'] == 2
    assert 'Synthetic test answer' not in str(report)


@pytest.mark.parametrize('change', ['duplicate', 'overlap', 'tuned', 'unknown_label', 'empty', 'unreviewed', 'bad_prediction'])
def test_invalid_or_leaking_dataset_is_rejected(change):
    data = deepcopy(dataset())
    if change == 'duplicate': data['records'][1]['id'] = data['records'][0]['id']
    elif change == 'overlap': data['records'][3]['source_group'] = data['records'][0]['source_group']
    elif change == 'tuned': data['records'][3]['used_for_tuning'] = True
    elif change == 'unknown_label': data['records'][3]['expected'] = 'made-up'
    elif change == 'empty': data['records'] = []
    elif change == 'unreviewed': data['records'][3]['reviewer_id'] = ''
    elif change == 'bad_prediction': data['records'][3]['prediction']['code'] = 'made-up'
    with pytest.raises(ValueError): evaluate(data, allow_synthetic=True)


def test_synthetic_data_cannot_be_called_independent_educator_evaluation():
    with pytest.raises(ValueError): evaluate(dataset())
