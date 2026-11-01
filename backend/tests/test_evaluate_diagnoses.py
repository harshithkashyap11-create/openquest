from scripts.evaluate_diagnoses import evaluate_labels


def test_offline_evaluation_normalizes_correct_label_and_counts_unmatched_rows():
    report = evaluate_labels(
        [
            {
                "student_id": "S001",
                "question_id": "Q01",
                "expected_label": "Correct",
            },
            {
                "student_id": "S002",
                "question_id": "Q01",
                "expected_label": "M01",
            },
        ],
        {
            ("S001", "Q01"): "CORRECT",
        },
    )

    assert report == {
        "total_ground_truth": 2,
        "total_evaluated": 1,
        "coverage": 0.5,
        "correct_predictions": 1,
        "incorrect_predictions": 0,
        "accuracy": 1.0,
        "confusion_matrix": {"CORRECT": {"CORRECT": 1}},
    }
