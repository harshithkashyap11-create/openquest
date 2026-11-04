import pytest
from scripts.evaluation_metrics import metrics


def test_metrics_count_abstention_and_unsupported_outputs_as_missed_labels():
    rows=[{'subject':'Mathematics','expected':'M01','predicted':'M01'},
          {'subject':'Science','expected':'FM01','predicted':'FOLLOW_UP'},
          {'subject':'English','expected':'SV01','predicted':'made-up'}]
    report=metrics(rows)
    assert report['sample_count']==3
    assert report['macro_f1']==pytest.approx(1/3)
    assert report['abstention_rate']==pytest.approx(1/3)
    assert report['unsupported_output_rate']==pytest.approx(1/3)
    assert report['subject_counts']=={'English':1,'Mathematics':1,'Science':1}
