"""Quiz contracts: grades, privacy, evidence, and live aggregates."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models import Class, Student, Teacher


@pytest.fixture
def quiz_env(db_session):
    teacher = Teacher(name="Quiz teacher", email=f"{uuid4()}@example.test")
    classroom = Class(class_name="Quiz lab", teacher=teacher)
    other = Class(class_name="Other lab", teacher=teacher)
    students = [Student(student_code=f"Q{i}", classroom=classroom) for i in range(3)]
    outsider = Student(student_code="OUT", classroom=other)
    db_session.add_all([teacher, classroom, other, *students, outsider])
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client, classroom, students, outsider
    app.dependency_overrides.clear()


def teacher_headers(classroom):
    return {"X-Demo-Role": "teacher", "X-Class-ID": str(classroom.id)}


def student_headers(student):
    return {"X-Student-ID": str(student.id)}


def quiz_payload():
    return {
        "title": "Fractions checkpoint",
        "questions": [
            {
                "text": "What is 1/2 + 1/3?",
                "options": ["2/5", "5/6", "1/6", "2/6"],
                "correct_option": 1,
                "explanation": "Use sixths: 3/6 + 2/6 = 5/6.",
                "concept": "Common denominators",
                "repair": {
                    "text": "What is 1/2 + 1/4?",
                    "options": ["2/6", "3/4", "1/8", "2/4"],
                    "correct_option": 1,
                    "explanation": "Use quarters: 2/4 + 1/4 = 3/4.",
                    "hint": "Express one half in quarters first.",
                },
            }
        ],
    }


def create_quiz(env, publish=True):
    client, classroom, _, _ = env
    response = client.post(
        f"/api/classes/{classroom.id}/quizzes",
        json=quiz_payload(),
        headers=teacher_headers(classroom),
    )
    assert response.status_code == 201, response.text
    quiz = response.json()
    if publish:
        response = client.post(
            f"/api/quizzes/{quiz['id']}/publish", headers=teacher_headers(classroom)
        )
        assert response.status_code == 200, response.text
    return quiz


def submit(env, quiz, student_index=0, option=0):
    client, _, students, _ = env
    student = students[student_index]
    return client.post(
        f"/api/students/{student.id}/quizzes/{quiz['id']}/submit",
        headers=student_headers(student),
        json={
            "answers": [
                {"question_id": quiz["questions"][0]["id"], "selected_option": option}
            ]
        },
    )


def reflect(env, quiz, message="I added the numerators and denominators together."):
    client, _, students, _ = env
    student = students[0]
    return client.post(
        f"/api/students/{student.id}/quizzes/{quiz['id']}/questions/{quiz['questions'][0]['id']}/reflect",
        headers=student_headers(student),
        json={"message": message, "language": "en"},
    )


def test_draft_hidden_publish_immutable_and_keys_hidden(quiz_env):
    client, classroom, students, _ = quiz_env
    student = students[0]
    quiz = create_quiz(quiz_env, publish=False)
    url = f"/api/students/{student.id}/quizzes"
    assert client.get(url, headers=student_headers(student)).json() == []
    assert (
        client.get(f"{url}/{quiz['id']}", headers=student_headers(student)).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/quizzes/{quiz['id']}/publish", headers=teacher_headers(classroom)
        ).status_code
        == 200
    )
    data = client.get(f"{url}/{quiz['id']}", headers=student_headers(student)).json()
    assert data["attempt"] is None
    assert "correct_option" not in str(data)
    assert "explanation" not in str(data["questions"])
    assert len(client.get(url, headers=student_headers(student)).json()) == 1
    assert (
        client.patch(
            f"/api/quizzes/{quiz['id']}",
            headers=teacher_headers(classroom),
            json=quiz_payload(),
        ).status_code
        == 409
    )


def test_grading_and_idempotent_duplicate_submission(quiz_env):
    quiz = create_quiz(quiz_env)
    first = submit(quiz_env, quiz)
    assert first.status_code == 200
    assert first.json()["score"] == 0
    assert first.json()["total"] == 1
    second = submit(quiz_env, quiz, option=1)
    assert second.json()["score"] == 0
    client, classroom, _, _ = quiz_env
    report = client.get(
        f"/api/quizzes/{quiz['id']}/insights", headers=teacher_headers(classroom)
    ).json()
    assert report["submitted_students"] == 1
    assert report["questions"][0]["option_counts"] == [1, 0, 0, 0]


def test_student_boundaries_and_teacher_scope(quiz_env):
    client, classroom, students, outsider = quiz_env
    quiz = create_quiz(quiz_env)
    url = f"/api/students/{students[0].id}/quizzes/{quiz['id']}"
    assert client.get(url, headers=student_headers(students[1])).status_code == 403
    outsider_url = f"/api/students/{outsider.id}/quizzes/{quiz['id']}"
    assert (
        client.get(outsider_url, headers=student_headers(outsider)).status_code == 404
    )
    assert (
        client.get(
            f"/api/quizzes/{quiz['id']}/insights", headers=student_headers(students[0])
        ).status_code
        == 422
    )
    wrong_scope = {"X-Demo-Role": "teacher", "X-Class-ID": str(outsider.class_id)}
    assert (
        client.get(
            f"/api/quizzes/{quiz['id']}/insights", headers=wrong_scope
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "answers",
    [
        [],
        [{"question_id": str(uuid4()), "selected_option": 0}],
        [{"question_id": "replace", "selected_option": 9}],
    ],
)
def test_invalid_answers_do_not_create_attempts(quiz_env, answers):
    client, classroom, students, _ = quiz_env
    quiz = create_quiz(quiz_env)
    if answers and answers[0]["question_id"] == "replace":
        answers[0]["question_id"] = quiz["questions"][0]["id"]
    result = client.post(
        f"/api/students/{students[0].id}/quizzes/{quiz['id']}/submit",
        headers=student_headers(students[0]),
        json={"answers": answers},
    )
    assert result.status_code == 422
    assert (
        client.get(
            f"/api/quizzes/{quiz['id']}/insights", headers=teacher_headers(classroom)
        ).json()["submitted_students"]
        == 0
    )


def test_reflection_requires_submission_and_evidence_precedes_repair(quiz_env):
    client, _, students, _ = quiz_env
    quiz = create_quiz(quiz_env)
    assert reflect(quiz_env, quiz).status_code == 409
    submit(quiz_env, quiz)
    result = reflect(quiz_env, quiz)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["feedback"]["provider"] == "template"
    assert data["feedback"]["error_type"] in {"procedure", "uncertain"}
    if data["feedback"]["error_type"] != "uncertain":
        assert (
            data["feedback"]["evidence"]
            in "I added the numerators and denominators together."
        )
    assert len(data["messages"]) == 2
    assert "correct_option" not in str(data["repair"])
    repair_url = f"/api/students/{students[0].id}/quizzes/{quiz['id']}/questions/{quiz['questions'][0]['id']}/repair"
    repaired = client.post(
        repair_url, headers=student_headers(students[0]), json={"selected_option": 1}
    )
    assert repaired.status_code == 200
    assert repaired.json()["is_correct"] is True
    assert (
        client.post(
            repair_url,
            headers=student_headers(students[0]),
            json={"selected_option": 0},
        ).json()["is_correct"]
        is True
    )
    state = client.get(
        f"/api/students/{students[0].id}/quizzes/{quiz['id']}",
        headers=student_headers(students[0]),
    ).json()
    assert (
        state["attempt"]["results"][0]["reflection"]["repair"]["result"]["is_correct"]
        is True
    )


def test_guessed_answer_stays_uncertain_and_review_changes_aggregates(quiz_env):
    client, classroom, _, _ = quiz_env
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    response = reflect(quiz_env, quiz, "I guessed and I am not sure.")
    assert response.status_code == 200
    reflection = response.json()
    assert reflection["feedback"]["error_type"] == "uncertain"
    report_url = f"/api/quizzes/{quiz['id']}/insights"
    report = client.get(report_url, headers=teacher_headers(classroom)).json()
    assert report["questions"][0]["reflected_students"] == 1
    assert report["questions"][0]["uncertain_students"] == 1
    assert report["questions"][0]["themes"] == []
    assert len(report["questions"][0]["evidence"]) == 1
    review = client.patch(
        f"/api/quizzes/{quiz['id']}/reflections/{reflection['id']}/review",
        headers=teacher_headers(classroom),
        json={"flagged": True},
    )
    assert review.status_code == 200
    report = client.get(report_url, headers=teacher_headers(classroom)).json()
    assert report["questions"][0]["flagged_students"] == 1


def test_csv_preview_quotes_bom_and_row_errors(quiz_env):
    client, classroom, _, _ = quiz_env
    headers = teacher_headers(classroom)
    csv = '\ufeffquestion,option_a,option_b,option_c,option_d,correct_option,explanation,concept\n"What is 1/2 + 1/3, in simplest form?",2/5,5/6,1/6,2/6,B,"Use sixths, then add.",Fractions\n'
    response = client.post(
        "/api/quizzes/import", headers=headers, json={"content": csv}
    )
    assert response.status_code == 200, response.text
    assert response.json()["questions"][0]["correct_option"] == 1
    assert response.json()["errors"] == []
    bad = csv.replace(",B,", ",Z,")
    response = client.post(
        "/api/quizzes/import", headers=headers, json={"content": bad}
    )
    assert response.json()["questions"] == []
    assert "2" in response.json()["errors"][0]
    assert client.post(
        "/api/quizzes/import", headers=headers, json={"content": "bad,headers\na,b"}
    ).json()["errors"]


def test_teacher_lesson_is_grounded_saved_and_reviewable(quiz_env):
    client, classroom, _, _ = quiz_env
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    reflect(quiz_env, quiz)
    url = f"/api/quizzes/{quiz['id']}/lesson"
    response = client.post(url, headers=teacher_headers(classroom))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "draft"
    assert response.json()["based_on_submissions"] == 1
    assert response.json()["provider"] == "template"
    edited = client.patch(
        url,
        headers=teacher_headers(classroom),
        json={
            "status": "accepted",
            "text": "Use fraction strips in pairs for five minutes.",
        },
    )
    assert edited.json()["status"] == "accepted"
    assert edited.json()["text"] == "Use fraction strips in pairs for five minutes."
    submit(quiz_env, quiz, student_index=1, option=1)
    report = client.get(
        f"/api/quizzes/{quiz['id']}/insights", headers=teacher_headers(classroom)
    ).json()
    assert report["submitted_students"] == 2
    assert report["lesson"]["based_on_submissions"] == 1
    assert report["questions"][0]["correct_students"] == 1


def test_bad_quiz_and_empty_reflection_rejected(quiz_env):
    client, classroom, _, _ = quiz_env
    payload = quiz_payload()
    payload["questions"][0]["correct_option"] = 4
    assert (
        client.post(
            f"/api/classes/{classroom.id}/quizzes",
            headers=teacher_headers(classroom),
            json=payload,
        ).status_code
        == 422
    )
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    assert reflect(quiz_env, quiz, "   ").status_code == 422


def configure_live(monkeypatch, completion):
    from types import SimpleNamespace
    from app.services import quiz_tutor

    monkeypatch.setattr(
        quiz_tutor,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="openrouter",
            openrouter_api_key="test-key",
            openrouter_model="test/model",
            openrouter_base_url="https://example.test",
            openrouter_timeout_seconds=1,
        ),
    )
    monkeypatch.setattr(quiz_tutor.OpenRouterChatClient, "complete_json", completion)


def test_live_tutor_verifies_quote_and_sends_only_question_context(
    quiz_env, monkeypatch
):
    import json

    captured = []

    def complete(_self, *, prompt, temperature):
        captured.append(prompt)
        return json.dumps(
            {
                "error_type": "procedure",
                "evidence": "I added the numerators and denominators together.",
                "reply": "Keep the denominator as the unit. Use sixths before adding. Which step would change?",
            }
        )

    configure_live(monkeypatch, complete)
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    result = reflect(quiz_env, quiz).json()
    assert result["feedback"]["provider"] == "openrouter"
    assert result["feedback"]["error_type"] == "procedure"
    assert "student_id" not in captured[0]
    assert "repair" not in captured[0]
    client, classroom, _, _ = quiz_env
    report = client.get(
        f"/api/quizzes/{quiz['id']}/insights", headers=teacher_headers(classroom)
    ).json()
    assert report["questions"][0]["themes"] == [
        {"error_type": "procedure", "students": 1}
    ]
    assert (
        client.patch(
            f"/api/quizzes/{quiz['id']}/reflections/{result['id']}/review",
            headers=teacher_headers(classroom),
            json={"flagged": True},
        ).status_code
        == 200
    )
    report = client.get(
        f"/api/quizzes/{quiz['id']}/insights", headers=teacher_headers(classroom)
    ).json()
    assert report["questions"][0]["themes"] == []


def test_unverifiable_model_quote_cannot_become_a_theme(quiz_env, monkeypatch):
    configure_live(
        monkeypatch,
        lambda *args, **kwargs: (
            '{"error_type":"concept","evidence":"a quote the student never wrote","reply":"Use sixths."}'
        ),
    )
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    response = reflect(quiz_env, quiz)
    assert response.status_code == 200
    assert response.json()["feedback"]["error_type"] == "uncertain"
    assert response.json()["feedback"]["evidence"] == ""


def test_explicit_guess_remains_uncertain_even_if_model_classifies_it(
    quiz_env, monkeypatch
):
    configure_live(
        monkeypatch,
        lambda *args, **kwargs: (
            '{"error_type":"concept","evidence":"I guessed","reply":"Let us compare the methods."}'
        ),
    )
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    response = reflect(quiz_env, quiz, "I guessed")
    assert response.json()["feedback"]["error_type"] == "uncertain"


@pytest.mark.parametrize(
    "provider_reply",
    ["not JSON", '{"error_type":"unsupported","evidence":"I added","reply":"hello"}'],
)
def test_malformed_model_response_does_not_persist_reflection(
    quiz_env, monkeypatch, provider_reply
):
    configure_live(monkeypatch, lambda *args, **kwargs: provider_reply)
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    response = reflect(quiz_env, quiz)
    assert response.status_code == 503
    client, classroom, _, _ = quiz_env
    assert (
        client.get(
            f"/api/quizzes/{quiz['id']}/insights", headers=teacher_headers(classroom)
        ).json()["questions"][0]["reflected_students"]
        == 0
    )


def test_provider_failure_keeps_score_and_student_can_retry(quiz_env, monkeypatch):
    from app.services.diagnosis_provider import ProviderError

    def fail(*args, **kwargs):
        raise ProviderError("upstream failure")

    configure_live(monkeypatch, fail)
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    assert reflect(quiz_env, quiz).status_code == 503
    client, _, students, _ = quiz_env
    state = client.get(
        f"/api/students/{students[0].id}/quizzes/{quiz['id']}",
        headers=student_headers(students[0]),
    ).json()
    assert state["attempt"]["score"] == 0
    assert state["attempt"]["results"][0]["reflection"] is None
    configure_live(
        monkeypatch,
        lambda *args, **kwargs: (
            '{"error_type":"uncertain","evidence":"I added","reply":"Let us review the teacher explanation."}'
        ),
    )
    assert reflect(quiz_env, quiz).status_code == 200


def test_diagnosis_chat_is_bounded(quiz_env):
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    for _ in range(5):
        assert reflect(quiz_env, quiz).status_code == 200
    assert reflect(quiz_env, quiz).status_code == 429


def test_live_next_lesson_is_generated_without_student_identifiers(
    quiz_env, monkeypatch
):
    import json

    captured = []

    def complete(_self, *, prompt, temperature):
        captured.append(prompt)
        return json.dumps(
            {
                "text": "Use fraction strips. Ask pairs to express both fractions in sixths, then use the approved repair question."
            }
        )

    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    reflect(quiz_env, quiz)
    configure_live(monkeypatch, complete)
    client, classroom, _, _ = quiz_env
    response = client.post(
        f"/api/quizzes/{quiz['id']}/lesson", headers=teacher_headers(classroom)
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "openrouter"
    assert response.json()["based_on_submissions"] == 1
    assert len(captured) == 1
    assert "student_code" not in captured[0]
    assert "student_id" not in captured[0]


def test_existing_teacher_copilot_includes_published_quiz_evidence(quiz_env):
    client, classroom, _, _ = quiz_env
    quiz = create_quiz(quiz_env)
    submit(quiz_env, quiz)
    reflect(quiz_env, quiz)
    response = client.post(
        "/api/copilot/chat",
        json={"message": "Analyze my class", "class_id": str(classroom.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert (
        data["class_context_summary"]["quiz_reports"][0]["title"]
        == "Fractions checkpoint"
    )
    assert data["class_context_summary"]["quiz_reports"][0]["submitted_students"] == 1
    assert "Fractions checkpoint" in data["reply"]
    assert "Question 1" in data["reply"]


def test_short_optional_csv_columns_return_validation_error_instead_of_crashing(
    quiz_env,
):
    client, classroom, _, _ = quiz_env
    content = "question,option_a,option_b,option_c,option_d,correct_option,explanation,repair_question\nQ,A,B,C,D,A,Explain\n"
    response = client.post(
        "/api/quizzes/import",
        headers=teacher_headers(classroom),
        json={"content": content},
    )
    assert response.status_code == 200
    assert response.json()["errors"]
