from fractions import Fraction
import uuid
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models import (
    Class,
    Diagnosis,
    GroupMember,
    InterventionAssignment,
    LearningGroup,
    PracticeResponse,
    Question,
    ReassessmentResult,
    Student,
    Submission,
    Teacher,
)
from app.services.answer_evaluation import answers_match
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
)
from app.services.intervention_provider import OpenRouterInterventionProvider
from app.services.intervention_service import (
    INTERVENTION_TEMPLATES,
    InterventionNotAllowedError,
    generate_intervention_for_group,
)
from app.services.progress_service import get_class_progress
from app.services.reassessment_service import REASSESSMENT_QUESTIONS


def _approved_group(db, code: str, student_count: int = 1):
    teacher = Teacher(
        name=f"Teacher {code}", email=f"teacher-{code}-{uuid4()}@example.test"
    )
    classroom = Class(class_name=f"Class {code} {uuid4()}", teacher=teacher)
    group = LearningGroup(
        classroom=classroom,
        topic="Fractions",
        misconception_code=code,
        name=f"{code} group",
        review_status="approved",
        teacher_approved=True,
    )
    students = [
        Student(classroom=classroom, student_code=f"{code}-{index}")
        for index in range(student_count)
    ]
    db.add_all([teacher, classroom, group, *students])
    db.flush()
    db.add_all(
        [
            GroupMember(group_id=group.id, student_id=student.id)
            for student in students
        ]
    )
    db.commit()
    return classroom, group, students


class _Personalizer:
    def personalize(self, **kwargs):
        assert kwargs["misconception_code"] == "M01"
        assert kwargs["learning_gap"] == ["Adds the denominators directly."]
        assert not {"expected_answers", "answer_key", "ground_truth"} & kwargs.keys()
        return {
            "explanation": "Personalized: use equal-sized parts before adding.",
            "instructions": "Rewrite each fraction with the same denominator.",
            "introduction": "Let's solve this together.",
            "hints": ["Find a shared denominator."],
        }


class _UnavailablePersonalizer:
    def personalize(self, **_kwargs):
        raise ProviderError("offline")


@pytest.mark.parametrize("code", ["M01", "M02", "M03", "M04", "M05"])
def test_generates_targeted_interventions_with_verified_keys(db_session, code):
    _, group, _ = _approved_group(db_session, code)

    intervention, assignments, created = generate_intervention_for_group(
        db_session, group.id
    )

    template = INTERVENTION_TEMPLATES[code]
    assert intervention.misconception_code == code
    assert intervention.title == template.title
    assert intervention.learning_objective
    assert intervention.guided_example["question"]
    assert len(intervention.practice_questions) == 3
    assert len(intervention.expected_answers) == 3
    assert len(assignments) == created == 1
    verified_practice_answers = {
        "M01": (
            Fraction(1, 4) + Fraction(1, 6),
            Fraction(2, 5) + Fraction(1, 10),
            Fraction(3, 4) + Fraction(1, 8),
        ),
        "M02": (
            max(Fraction(5, 6), Fraction(5, 8)),
            max(Fraction(2, 3), Fraction(3, 5)),
            max(Fraction(3, 8), Fraction(1, 2)),
        ),
        "M03": (Fraction(1, 3), Fraction(2, 5), Fraction(3, 4)),
        "M04": ("Yes", "No", "Yes"),
        "M05": (
            Fraction(4, 7) + Fraction(2, 7),
            Fraction(5, 6) - Fraction(1, 6),
            Fraction(7, 10) - Fraction(3, 10),
        ),
    }[code]
    assert all(
        answers_match(expected, str(verified))
        for expected, verified in zip(
            template.expected_answers, verified_practice_answers, strict=True
        )
    )
    assert intervention.expected_answers == list(template.expected_answers)


def test_m06_requires_diagnostic_followup_not_remediation(db_session):
    _, group, _ = _approved_group(db_session, "M06")

    with pytest.raises(InterventionNotAllowedError, match="diagnostic follow-up"):
        generate_intervention_for_group(db_session, group.id)


def test_teacher_approval_is_required(db_session):
    _, group, _ = _approved_group(db_session, "M01")
    group.teacher_approved = False
    group.review_status = "proposed"
    db_session.commit()

    with pytest.raises(PermissionError, match="Teacher approval"):
        generate_intervention_for_group(db_session, group.id)


def test_openrouter_personalizes_only_text_and_template_fallback_is_identified(
    db_session,
):
    _, group, students = _approved_group(db_session, "M01")
    question = Question(
        topic="Fractions",
        question_text="Explain why denominators cannot be added.",
        correct_answer="Use a common denominator",
    )
    submission = Submission(
        student_id=students[0].id,
        question=question,
        answer="2/5",
        explanation="Adds the denominators directly.",
    )
    db_session.add(submission)
    db_session.flush()
    db_session.add(
        Diagnosis(
            submission_id=submission.id,
            misconception_code="M01",
            confidence=0.9,
            evidence="Adds the denominators directly.",
        )
    )
    db_session.commit()

    personalized, _, _ = generate_intervention_for_group(
        db_session, group.id, personalizer=_Personalizer()
    )
    assert personalized.provider == "openrouter"
    assert personalized.explanation.startswith("Personalized")
    assert personalized.expected_answers == ["5/12", "1/2", "7/8"]

    fallback_group = _approved_group(db_session, "M02")[1]
    fallback, _, _ = generate_intervention_for_group(
        db_session, fallback_group.id, personalizer=_UnavailablePersonalizer()
    )
    assert fallback.provider == "template"
    assert "OpenRouter failed" in fallback.generation_note
    assert fallback.expected_answers == ["5/6", "2/3", "1/2"]


def test_openrouter_intervention_provider_parses_personalization():
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"explanation":"Use equal parts.",'
                            '"instructions":"Find a common denominator.",'
                            '"introduction":"Let us compare fractions.",'
                            '"hints":["Make the parts equal."]}'
                        )
                    }
                }
            ]
        },
    )
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: response)
    )
    provider = OpenRouterInterventionProvider(
        api_key="test-key-not-real",
        model="provider/model",
        client=client,
    )

    result = provider.personalize(
        misconception_code="M01",
        taxonomy_description="Adds denominators directly",
        learning_objective="Use a common denominator",
        learning_gap=["Adds the denominators directly."],
        explanation="Template explanation",
        instructions="Template instructions",
        introduction="Template introduction",
        hints=["Template hint"],
    )

    assert result.explanation == "Use equal parts."
    assert result.hints == ["Make the parts equal."]


def test_missing_openrouter_key_is_not_hidden_by_intervention_template_fallback(
    db_session, monkeypatch
):
    _, group, _ = _approved_group(db_session, "M01")
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_MODEL", "provider/model")
    try:
        with pytest.raises(ProviderConfigurationError, match="OPENROUTER_API_KEY"):
            generate_intervention_for_group(db_session, group.id)
    finally:
        get_settings.cache_clear()


def test_assignment_creation_is_idempotent_for_group_members(db_session):
    _, group, students = _approved_group(db_session, "M03", student_count=2)

    _, assignments, created = generate_intervention_for_group(db_session, group.id)
    _, second_assignments, second_created = generate_intervention_for_group(
        db_session, group.id
    )

    assert created == 2
    assert second_created == 0
    assert {item.student_id for item in assignments} == {
        student.id for student in students
    }
    assert [item.id for item in assignments] == [item.id for item in second_assignments]
    assert db_session.query(InterventionAssignment).count() == 2


def test_reassessment_catalog_is_distinct_and_answer_keys_are_correct():
    initial_questions = {
        "Calculate 1/2 + 1/3.",
        "Which is larger, 1/4 or 1/8?",
        "Are 1/2 and 2/4 equivalent?",
        "Add 1/3 + 1/6.",
        "Compare 2/3 and 3/4.",
    }
    for template_set in REASSESSMENT_QUESTIONS.values():
        assert len(template_set) == 3
        assert not initial_questions.intersection(
            question for question, _, _ in template_set
        )
        assert all(question and answer for question, answer, _ in template_set)
    assert answers_match("2/4", "1/2")
    assert not answers_match("", "1/2")
    assert not answers_match("2/0", "1/2")
    assert not answers_match(None, "1/2")
    verified_reassessment_answers = {
        "M01": (
            Fraction(2, 3) + Fraction(1, 4),
            Fraction(3, 5) + Fraction(1, 10),
            Fraction(1, 6) + Fraction(3, 8),
        ),
        "M02": (
            max(Fraction(3, 7), Fraction(3, 5)),
            max(Fraction(4, 9), Fraction(1, 2)),
            max(Fraction(5, 8), Fraction(2, 3)),
        ),
        "M03": (Fraction(2, 7), Fraction(3, 8), Fraction(5, 6)),
        "M04": ("Yes", "No", "Yes"),
        "M05": (
            Fraction(5, 9) + Fraction(2, 9),
            Fraction(7, 8) - Fraction(3, 8),
            Fraction(4, 5) + Fraction(1, 10),
        ),
    }
    for code, verified in verified_reassessment_answers.items():
        assert all(
            answers_match(answer, str(value))
            for (_, answer, _), value in zip(
                REASSESSMENT_QUESTIONS[code], verified, strict=True
            )
        )


def _client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_student_workflow_reassessment_scoring_and_progress(db_session):
    classroom, group, students = _approved_group(db_session, "M01")
    student = students[0]
    baseline_question = Question(
        topic="Fractions",
        question_text="Baseline sample for progress.",
        correct_answer="1/2",
    )
    db_session.add(
        Submission(student_id=student.id, question=baseline_question, answer="2/5")
    )
    db_session.commit()
    client = _client(db_session)
    student_headers = {"X-Student-ID": str(student.id)}
    try:
        generated = client.post(
            f"/api/groups/{group.id}/interventions/generate"
        )
        assert generated.status_code == 200
        generation = generated.json()
        assert generation["assignments_created"] == 1
        assignment_id = generation["assignments"][0]["id"]

        repeated = client.post(f"/api/groups/{group.id}/interventions/generate")
        assert repeated.json()["assignments_created"] == 0

        student_list = client.get(
            f"/api/students/{student.id}/interventions", headers=student_headers
        )
        assert student_list.status_code == 200
        assigned_activity = student_list.json()[0]
        assert "expected_answers" not in assigned_activity["intervention"]
        assert assigned_activity["status"] == "assigned"
        own_assignment = client.get(
            f"/api/intervention-assignments/{assignment_id}",
            headers=student_headers,
        )
        assert own_assignment.status_code == 200

        another_student_id = uuid4()
        assert client.get(
            f"/api/students/{student.id}/interventions",
            headers={"X-Student-ID": str(another_student_id)},
        ).status_code == 403
        assert client.get(
            f"/api/intervention-assignments/{assignment_id}",
            headers={"X-Student-ID": str(another_student_id)},
        ).status_code == 403

        practice = client.post(
            f"/api/intervention-assignments/{assignment_id}/submit",
            headers=student_headers,
            json={
                "answers": [
                    {"question_index": 0, "answer": "5/12", "is_correct": False},
                    {"question_index": 1, "answer": "2/4"},
                ]
            },
        )
        assert practice.status_code == 200
        assert practice.json()["status"] == "in_progress"
        assert practice.json()["correct_answers"] == 2
        assert db_session.query(PracticeResponse).count() == 2
        assert db_session.query(InterventionAssignment).one().started_at is not None

        client.post(f"/api/intervention-assignments/{assignment_id}/submit", headers=student_headers,
            json={"answers": [{"question_index": i, "answer": a} for i, a in enumerate(["5/12", "1/2", "7/8"])]})
        completed = client.post(
            f"/api/intervention-assignments/{assignment_id}/complete",
            headers=student_headers,
        )
        assert completed.status_code == 200
        assert completed.json()["assignment"]["status"] == "completed"
        assert completed.json()["assignment"]["completed_at"] is not None
        assert len(completed.json()["assignment"]["practice_responses"]) == 3
        assert completed.json()["assignment"]["practice_responses"][0]["question_index"] == 0
        quiz = completed.json()["reassessment"]
        assert len(quiz["questions"]) == 3
        assert quiz["misconception_code"] == "M01"
        assert quiz["status"] == "pending"

        repeated_quiz = client.post(
            f"/api/intervention-assignments/{assignment_id}/reassessment",
            headers=student_headers,
        )
        assert repeated_quiz.json()["id"] == quiz["id"]
        answer_values = ["11/12", "7/10", ""]
        submitted = client.post(
            f"/api/reassessments/{quiz['id']}/submit",
            headers=student_headers,
            json={
                "answers": [
                    {"question_id": item["id"], "answer": answer_values[index]}
                    for index, item in enumerate(quiz["questions"])
                ]
            },
        )
        assert submitted.status_code == 200
        result = submitted.json()
        assert result["correct_answers"] == 2
        assert result["incorrect_answers"] == 1
        assert result["accuracy_percentage"] == 66.7
        assert db_session.query(ReassessmentResult).count() == 3

        reassessment_get = client.get(
            f"/api/reassessments/{quiz['id']}",
            headers=student_headers,
        )
        assert reassessment_get.status_code == 200
        assert reassessment_get.json()["id"] == quiz["id"]
        assert reassessment_get.json()["correct_answers"] == 2
        assert len(reassessment_get.json()["results"]) == 3

        progress = client.get(f"/api/classes/{classroom.id}/progress")
        assert progress.status_code == 200
        analytics = progress.json()
        assert analytics["assigned_interventions"] == 1
        assert analytics["completed_interventions"] == 1
        assert analytics["completed_reassessments"] == 1
        assert analytics["initial_assessment"] == {
            "accuracy_percentage": 0.0,
            "sample_size": 1,
            "correct_answers": 0,
        }
        assert analytics["followup_assessment"]["sample_size"] == 3
        assert analytics["followup_assessment"]["accuracy_percentage"] == 66.7
        assert analytics["accuracy_change_percentage_points"] == 66.7
        assert "do not establish causal improvement" in analytics[
            "progress_interpretation"
        ]
        assert analytics["students_needing_support"][0]["student_id"] == str(student.id)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_reassessment_submission_requires_owner_and_grades_empty_answers(db_session):
    _, group, students = _approved_group(db_session, "M02")
    _, assignments, _ = generate_intervention_for_group(db_session, group.id)
    assignments[0].status = "completed"
    db_session.commit()
    from app.services.reassessment_service import generate_reassessment, submit_reassessment

    reassessment = generate_reassessment(db_session, assignments[0].id)
    question_ids = {item.question_id for item in reassessment.questions}
    with pytest.raises(PermissionError, match="does not belong"):
        submit_reassessment(
            db_session,
            reassessment.id,
            {},
            student_id=uuid4(),
        )
    saved, results = submit_reassessment(
        db_session,
        reassessment.id,
        {},
        student_id=students[0].id,
    )
    assert saved.correct_answers == 0
    assert saved.incorrect_answers == 3
    assert len(results) == 3
    assert {result.question_id for result in results} == question_ids


def test_exact_denominator_enforcement_and_equivalence():
    prompt_d12 = "Write 1/3 with denominator 12."
    assert answers_match("4/12", "4/12", question_text=prompt_d12) is True
    assert answers_match(" 4 / 12 ", "4/12", question_text=prompt_d12) is True
    assert answers_match("1/3", "4/12", question_text=prompt_d12) is False
    assert answers_match("8/24", "4/12", question_text=prompt_d12) is False
    assert answers_match("5/12", "4/12", question_text=prompt_d12) is False
    assert answers_match("2/6", "4/12", question_text=prompt_d12) is False
    assert answers_match("", "4/12", question_text=prompt_d12) is False
    assert answers_match(None, "4/12", question_text=prompt_d12) is False
    assert answers_match("invalid", "4/12", question_text=prompt_d12) is False

    prompt_d15 = "Write 2/5 with denominator 15."
    assert answers_match("6/15", "6/15", question_text=prompt_d15) is True
    assert answers_match("2/5", "6/15", question_text=prompt_d15) is False

    prompt_equiv = "Are 1/2 and 2/4 equivalent?"
    assert answers_match("Yes", "Yes", question_text=prompt_equiv) is True
    assert answers_match("yes", "Yes", question_text=prompt_equiv) is True
    assert answers_match("No", "Yes", question_text=prompt_equiv) is False

    prompt_arith = "Add 1/4 + 1/6."
    assert answers_match("5/12", "5/12", question_text=prompt_arith) is True
    assert answers_match("10/24", "5/12", question_text=prompt_arith) is True


def test_baseline_analytics_accepts_valid_alternatives_and_synthetic_examples(db_session):
    teacher = Teacher(name="Baseline Teacher", email=f"base-{uuid4()}@example.test")
    classroom = Class(class_name=f"Base Class {uuid4()}", teacher=teacher)
    db_session.add_all([teacher, classroom])
    db_session.flush()

    q05_text = "Compare 2/3 and 3/4."
    q05 = Question(
        topic="Fractions",
        question_text=q05_text,
        correct_answer="3/4",
    )
    db_session.add(q05)
    db_session.flush()

    students = []
    for code in ["S010", "S020", "S030", "S040"]:
        s = Student(classroom=classroom, student_code=code)
        students.append(s)
    s_std = Student(classroom=classroom, student_code="S_STD")
    s_wrg = Student(classroom=classroom, student_code="S_WRG")
    db_session.add_all([*students, s_std, s_wrg])
    db_session.flush()

    submissions = []
    for s in students:
        sub = Submission(
            student=s,
            question=q05,
            answer="8/12 and 9/12",
            explanation="I made equivalent fractions with denominator 12.",
        )
        submissions.append(sub)
    submissions.append(Submission(student=s_std, question=q05, answer="3/4"))
    submissions.append(Submission(student=s_wrg, question=q05, answer="2/3"))

    db_session.add_all(submissions)
    db_session.commit()

    progress = get_class_progress(db_session, classroom.id)
    assert progress["initial_assessment"]["sample_size"] == 6
    assert progress["initial_assessment"]["correct_answers"] == 5
    assert progress["initial_assessment"]["accuracy_percentage"] == round(5 * 100 / 6, 1)


def test_m04_content_has_negative_counterexamples_and_reassessment_alignment():
    template = INTERVENTION_TEMPLATES["M04"]
    assert "No" in template.expected_answers
    assert "Yes" in template.expected_answers

    reassessment_set = REASSESSMENT_QUESTIONS["M04"]
    expected_reassessment_answers = [answer for _, answer, _ in reassessment_set]
    assert "No" in expected_reassessment_answers
    assert "Yes" in expected_reassessment_answers

    practice_prompts = set(template.practice_questions)
    reassessment_prompts = {prompt for prompt, _, _ in reassessment_set}
    assert not practice_prompts.intersection(reassessment_prompts)

    for prompt, _, _ in reassessment_set:
        assert "equivalent" in prompt.lower()
        assert "with denominator" not in prompt.lower()


def test_practice_response_retrieval_and_activity_resumption(db_session):
    _, group, students = _approved_group(db_session, "M01")
    student = students[0]
    client = _client(db_session)
    student_headers = {"X-Student-ID": str(student.id)}
    try:
        gen = client.post(f"/api/groups/{group.id}/interventions/generate")
        assignment_id = gen.json()["assignments"][0]["id"]

        resp = client.post(
            f"/api/intervention-assignments/{assignment_id}/submit",
            headers=student_headers,
            json={"answers": [{"question_index": 0, "answer": "5/12"}]},
        )
        assert resp.status_code == 200

        get_resp = client.get(
            f"/api/intervention-assignments/{assignment_id}",
            headers=student_headers,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert len(data["practice_responses"]) == 1
        assert data["practice_responses"][0]["question_index"] == 0
        assert data["practice_responses"][0]["answer"] == "5/12"
        assert data["practice_responses"][0]["is_correct"] is True
        assert data["practice_responses"][0]["submitted_at"]

        list_resp = client.get(
            f"/api/students/{student.id}/interventions",
            headers=student_headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()[0]
        assert len(list_data["practice_responses"]) == 1
        assert list_data["practice_responses"][0]["answer"] == "5/12"

        client.post(
            f"/api/intervention-assignments/{assignment_id}/submit",
            headers=student_headers,
            json={"answers": [{"question_index": 1, "answer": "1/2"}]},
        )
        get_resp2 = client.get(
            f"/api/intervention-assignments/{assignment_id}",
            headers=student_headers,
        )
        assert len(get_resp2.json()["practice_responses"]) == 2
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_reassessment_result_retrieval(db_session):
    _, group, students = _approved_group(db_session, "M01")
    student = students[0]
    other_student_id = uuid4()
    client = _client(db_session)
    student_headers = {"X-Student-ID": str(student.id)}
    try:
        gen = client.post(f"/api/groups/{group.id}/interventions/generate")
        assignment_id = gen.json()["assignments"][0]["id"]
        client.post(f"/api/intervention-assignments/{assignment_id}/submit", headers=student_headers,
            json={"answers": [{"question_index": i, "answer": a} for i, a in enumerate(["5/12", "1/2", "7/8"])]})
        completed = client.post(
            f"/api/intervention-assignments/{assignment_id}/complete",
            headers=student_headers,
        )
        quiz = completed.json()["reassessment"]

        pending_get = client.get(
            f"/api/reassessments/{quiz['id']}",
            headers=student_headers,
        )
        assert pending_get.status_code == 200
        assert pending_get.json()["status"] == "pending"
        assert pending_get.json()["results"] == []

        client.post(
            f"/api/reassessments/{quiz['id']}/submit",
            headers=student_headers,
            json={
                "answers": [
                    {"question_id": quiz["questions"][0]["id"], "answer": "11/12"},
                    {"question_id": quiz["questions"][1]["id"], "answer": "7/10"},
                    {"question_id": quiz["questions"][2]["id"], "answer": "1/2"},
                ]
            },
        )

        get_resp = client.get(
            f"/api/reassessments/{quiz['id']}",
            headers=student_headers,
        )
        assert get_resp.status_code == 200
        result_data = get_resp.json()
        assert result_data["id"] == quiz["id"]
        assert result_data["status"] == "completed"
        assert result_data["correct_answers"] == 2
        assert result_data["incorrect_answers"] == 1
        assert result_data["accuracy_percentage"] == 66.7
        assert len(result_data["results"]) == 3
        assert result_data["results"][0]["answer"] == "11/12"
        assert result_data["results"][0]["is_correct"] is True

        forbidden_resp = client.get(
            f"/api/reassessments/{quiz['id']}",
            headers={"X-Student-ID": str(other_student_id)},
        )
        assert forbidden_resp.status_code == 403

        not_found_resp = client.get(
            f"/api/reassessments/{uuid4()}",
            headers=student_headers,
        )
        assert not_found_resp.status_code == 404

        unauthorized_resp = client.get(f"/api/reassessments/{quiz['id']}")
        assert unauthorized_resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_failed_reassessment_generation_rolls_back_completion(db_session, monkeypatch):
    _, group, students = _approved_group(db_session, "M01")
    student = students[0]
    client = _client(db_session)
    student_headers = {"X-Student-ID": str(student.id)}
    try:
        gen = client.post(f"/api/groups/{group.id}/interventions/generate")
        assignment_id = gen.json()["assignments"][0]["id"]

        client.post(
            f"/api/intervention-assignments/{assignment_id}/submit",
            headers=student_headers,
            json={"answers": [{"question_index": i, "answer": a} for i, a in enumerate(["5/12", "1/2", "7/8"])]},
        )
        assignment = db_session.get(InterventionAssignment, UUID(assignment_id))
        assert assignment.status == "in_progress"

        import app.routes.interventions as routes_module

        def failing_generator(db, aid):
            raise ValueError("Simulated reassessment generation failure")

        monkeypatch.setattr(routes_module, "generate_reassessment", failing_generator)

        comp_resp = client.post(
            f"/api/intervention-assignments/{assignment_id}/complete",
            headers=student_headers,
        )
        assert comp_resp.status_code == 409

        db_session.expire_all()
        reloaded = db_session.get(InterventionAssignment, UUID(assignment_id))
        assert reloaded.status == "in_progress"
        assert reloaded.completed_at is None
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_duplicate_reassessment_prevention_on_repeated_complete(db_session):
    _, group, students = _approved_group(db_session, "M01")
    student = students[0]
    client = _client(db_session)
    student_headers = {"X-Student-ID": str(student.id)}
    try:
        gen = client.post(f"/api/groups/{group.id}/interventions/generate")
        assignment_id = gen.json()["assignments"][0]["id"]

        client.post(f"/api/intervention-assignments/{assignment_id}/submit", headers=student_headers,
            json={"answers": [{"question_index": i, "answer": a} for i, a in enumerate(["5/12", "1/2", "7/8"])]})
        first = client.post(
            f"/api/intervention-assignments/{assignment_id}/complete",
            headers=student_headers,
        )
        assert first.status_code == 200
        first_quiz_id = first.json()["reassessment"]["id"]

        second = client.post(
            f"/api/intervention-assignments/{assignment_id}/complete",
            headers=student_headers,
        )
        assert second.status_code == 200
        second_quiz_id = second.json()["reassessment"]["id"]

        assert first_quiz_id == second_quiz_id
        from app.models import Reassessment
        assert db_session.query(Reassessment).filter_by(assignment_id=UUID(assignment_id)).count() == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
