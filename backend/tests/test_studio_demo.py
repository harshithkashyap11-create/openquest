from sqlalchemy import select
from app.models.studio import StudioActivity, StudioSet, StudioWork
from test_classroom_studio import studio_env


def test_studio_demo_is_repeatable_and_has_no_fabricated_student_work(studio_env):
    from app.main import app
    from app.core.database import get_db
    from scripts.seed_studio_demo import seed_studio_examples
    db = app.dependency_overrides[get_db]()
    first = seed_studio_examples(db); second = seed_studio_examples(db)
    assert first['activities_created'] == 6 and second['activities_created'] == 0
    assert len(list(db.scalars(select(StudioActivity)))) == 6
    assert len(list(db.scalars(select(StudioSet)))) == 3
    assert list(db.scalars(select(StudioWork))) == []
