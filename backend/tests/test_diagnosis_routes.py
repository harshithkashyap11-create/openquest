import asyncio
import httpx

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models import Class, Question, Student, Submission, Teacher


async def _request(method, path, **kwargs):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, **kwargs)


def test_class_diagnosis_and_reviewable_group_routes(db_session, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    teacher = Teacher(name="Teacher", email="routes@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    question = Question(
        topic="Fractions",
        question_text="Calculate 1/2 + 1/3.",
        correct_answer="5/6",
    )
    db_session.add_all([teacher, question])
    db_session.flush()
    for index in range(2):
        student = Student(
            class_id=classroom.id,
            student_code=f"R{index:03d}",
        )
        db_session.add(student)
        db_session.flush()
        db_session.add(
            Submission(
                student_id=student.id,
                question_id=question.id,
                answer="2/5",
                explanation="I added the top numbers and the bottom numbers.",
            )
        )
    db_session.flush()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        run_response = asyncio.run(
            _request("POST", f"/api/classes/{classroom.id}/diagnose")
        )
        repeated_run_response = asyncio.run(
            _request("POST", f"/api/classes/{classroom.id}/diagnose")
        )
        list_response = asyncio.run(
            _request("GET", f"/api/classes/{classroom.id}/diagnoses")
        )
        summary_response = asyncio.run(
            _request("GET", f"/api/classes/{classroom.id}/diagnoses/summary")
        )
        groups_response = asyncio.run(
            _request("POST", f"/api/classes/{classroom.id}/groups/generate")
        )
        list_groups_response = asyncio.run(
            _request("GET", f"/api/classes/{classroom.id}/groups")
        )
        group_id = list_groups_response.json()[0]["id"]
        review_response = asyncio.run(
            _request(
                "PATCH",
                f"/api/groups/{group_id}/review",
                json={"status": "approved"},
            )
        )
    finally:
        app.dependency_overrides.pop(get_db, None)
        get_settings.cache_clear()

    assert run_response.status_code == 200
    assert run_response.json()["diagnosed"] == 2
    assert repeated_run_response.status_code == 200
    assert repeated_run_response.json()["diagnosed"] == 0
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2
    assert list_response.json()[0]["provider"] == "mock"
    assert list_response.json()[0]["student_code"].startswith("R")
    assert len(list_response.json()[0]["student_id"]) == 36  # UUID string
    assert summary_response.status_code == 200
    assert summary_response.json()["total_diagnoses"] == 2
    assert groups_response.status_code == 200
    assert len(groups_response.json()["groups"]) == 1
    assert list_groups_response.status_code == 200
    assert review_response.status_code == 200
    assert review_response.json()["review_status"] == "approved"


def test_diagnosis_batch_rejects_more_than_twenty_requested(db_session):
    teacher = Teacher(name="Teacher", email="batch-limit@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    db_session.add(classroom)
    db_session.flush()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = asyncio.run(
            _request(
                "POST",
                f"/api/classes/{classroom.id}/diagnose",
                params={"limit": 21},
            )
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
