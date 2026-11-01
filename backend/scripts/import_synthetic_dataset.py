import argparse
from pathlib import Path

from app.core.database import SessionLocal
from app.services.dataset_import import import_synthetic_dataset

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = REPOSITORY_ROOT / "data" / "synthetic_responses.csv"
MULTI_SUBJECT_DATASET_PATH = (
    REPOSITORY_ROOT / "data" / "multi_subject_synthetic_responses.csv"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import synthetic ClassPulse responses into the configured database."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help=f"CSV source path (default: {DEFAULT_DATASET_PATH})",
    )
    parser.add_argument(
        "--include-multisubject",
        action="store_true",
        help="Also import deterministic synthetic responses for the other five demo topics.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        dataset_paths = [args.csv]
        if args.include_multisubject:
            dataset_paths.append(MULTI_SUBJECT_DATASET_PATH)
        for dataset_path in dataset_paths:
            summary = import_synthetic_dataset(session, dataset_path)
            print(
                f"Imported {dataset_path.name}: "
                f"teachers created={summary.teachers_created}, "
                f"classes created={summary.classes_created}, "
                f"students created={summary.students_created}, "
                f"questions created={summary.questions_created}, "
                f"submissions created={summary.submissions_created}, "
                f"submissions reused={summary.submissions_reused}."
            )


if __name__ == "__main__":
    main()
