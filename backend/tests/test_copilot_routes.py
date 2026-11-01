from uuid import uuid4
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models import Class, Student, Teacher
from app.services.copilot_provider import MockCopilotProvider, OpenRouterCopilotProvider
from app.services.copilot_service import TeacherCopilotService
from app.services.diagnosis_provider import ProviderRateLimited, ProviderError


def _client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_copilot_chat_endpoint_without_class_id(db_session):
    client = _client(db_session)
    response = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "How do I teach fractions to beginners?",
            "subject": "Mathematics",
            "topic": "Fractions",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "Mathematics"
    assert data["topic"] == "Fractions"
    assert data["class_id"] is None
    assert data["provider"] in {"mock", "mock_fallback"}
    assert len(data["reply"]) > 0

    # Verify unversioned prefix also works seamlessly
    unversioned = client.post(
        "/api/copilot/chat",
        json={
            "message": "How do I teach fractions to beginners?",
            "subject": "Mathematics",
            "topic": "Fractions",
        },
    )
    assert unversioned.status_code == 200
    assert unversioned.json()["subject"] == "Mathematics"


def test_copilot_chat_endpoint_with_valid_class_id(db_session):
    teacher = Teacher(name="Test Teacher", email=f"test-{uuid4()}@classpulse.test")
    classroom = Class(class_name="Science 8", subject="Science", topic="Force and motion", teacher=teacher)
    student = Student(student_code="SCI001", classroom=classroom)
    db_session.add_all([teacher, classroom, student])
    db_session.commit()

    client = _client(db_session)
    response = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Summarize this class's performance and suggest a lesson plan",
            "class_id": str(classroom.id),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == str(classroom.id)
    assert data["subject"] == "Science"
    assert data["topic"] == "Force and motion"
    assert data["class_context_summary"] is not None
    assert data["class_context_summary"]["total_students"] == 1


def test_copilot_chat_endpoint_with_invalid_class_id_returns_404(db_session):
    client = _client(db_session)
    response = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Hello",
            "class_id": str(uuid4()),
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_copilot_chat_endpoint_with_empty_message_returns_422(db_session):
    client = _client(db_session)
    response = client.post(
        "/api/v1/copilot/chat",
        json={"message": ""},
    )
    assert response.status_code == 422


def test_copilot_chat_endpoint_with_conversation_history(db_session):
    client = _client(db_session)
    history = [
        {"role": "user", "content": "Tell me about Newton's First Law."},
        {"role": "assistant", "content": "An object in motion stays in motion unless acted upon by a net force."},
    ]
    response = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Can you generate 2 practice questions for this?",
            "subject": "Science",
            "topic": "Force and motion",
            "history": history,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["draft_content"] is not None
    assert len(data["draft_content"]["items"]) >= 2


def test_get_classroom_intelligence_context_endpoint(db_session):
    teacher = Teacher(name="Context Teacher", email=f"ctx-{uuid4()}@classpulse.test")
    classroom = Class(class_name="Math 6B", subject="Mathematics", topic="Fractions", teacher=teacher)
    student1 = Student(student_code="MTH01", classroom=classroom)
    student2 = Student(student_code="MTH02", classroom=classroom)
    db_session.add_all([teacher, classroom, student1, student2])
    db_session.commit()

    client = _client(db_session)
    response = client.get(f"/api/v1/copilot/classes/{classroom.id}/context")
    assert response.status_code == 200
    data = response.json()
    assert data["class_id"] == str(classroom.id)
    assert data["class_name"] == "Math 6B"
    assert data["total_students"] == 2


def test_get_classroom_intelligence_context_invalid_id_returns_404(db_session):
    client = _client(db_session)
    response = client.get(f"/api/v1/copilot/classes/{uuid4()}/context")
    assert response.status_code == 404


def test_list_supported_taxonomy_endpoint(db_session):
    client = _client(db_session)
    response = client.get("/api/v1/copilot/taxonomy")
    assert response.status_code == 200
    data = response.json()
    assert "Mathematics" in data
    assert "Science" in data
    assert "English" in data
    math_topics = [t["topic"] for t in data["Mathematics"]]
    assert "Fractions" in math_topics
    assert "Basic algebra" in math_topics


def test_copilot_chat_handles_rate_limiting_with_429(monkeypatch, db_session):
    def fake_generate(*args, **kwargs):
        raise ProviderRateLimited("OpenRouter rate limit exceeded")

    monkeypatch.setattr(MockCopilotProvider, "generate", fake_generate)

    client = _client(db_session)
    response = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Please summarize class"},
    )
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "30"
    assert "rate limit" in response.json()["detail"].lower()
