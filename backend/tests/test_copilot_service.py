from uuid import uuid4
import httpx
import pytest

from app.core.config import Settings
from app.models import (
    Class,
    Diagnosis,
    Intervention,
    InterventionAssignment,
    LearningGroup,
    Question,
    Reassessment,
    ReassessmentResult,
    Student,
    Submission,
    Teacher,
)
from app.schemas.copilot import (
    ChatMessage,
    CopilotChatRequest,
)
from app.services.copilot_provider import (
    MockCopilotProvider,
    OpenRouterCopilotProvider,
    create_copilot_provider,
    detect_intent,
    normalize_subject_topic,
)
from app.services.copilot_service import TeacherCopilotService
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderRateLimited,
)


def _seed_copilot_test_class(db_session, *, subject="Mathematics", topic="Fractions", code="M01"):
    teacher = Teacher(name="Teacher Ada", email=f"ada-{uuid4()}@classpulse.test")
    classroom = Class(class_name=f"{topic} 6A", subject=subject, topic=topic, teacher=teacher)
    student1 = Student(student_code="STU001", classroom=classroom)
    student2 = Student(student_code="STU002", classroom=classroom)

    question1 = Question(
        subject=subject,
        topic=topic,
        question_text=f"Test {topic} Question 1",
        correct_answer="5/6" if topic == "Fractions" else "x = 8",
    )
    question2 = Question(
        subject=subject,
        topic=topic,
        question_text=f"Test {topic} Question 2",
        correct_answer="1/4" if topic == "Fractions" else "3x + 12",
    )
    db_session.add_all([teacher, classroom, student1, student2, question1, question2])
    db_session.flush()

    sub1 = Submission(
        student_id=student1.id,
        question_id=question1.id,
        attempt_no=1,
        answer="2/5",
        explanation="I added top and bottom numbers directly.",
    )
    sub2 = Submission(
        student_id=student2.id,
        question_id=question1.id,
        attempt_no=1,
        answer="2/5",
        explanation="Added across numerators and denominators.",
    )
    db_session.add_all([sub1, sub2])
    db_session.flush()

    diag1 = Diagnosis(
        submission_id=sub1.id,
        misconception_code=code,
        confidence=0.95,
        evidence="I added top and bottom numbers directly.",
        status="confirmed",
        misconception_description="Adds numerators and denominators directly.",
    )
    diag2 = Diagnosis(
        submission_id=sub2.id,
        misconception_code=code,
        confidence=0.90,
        evidence="Added across numerators and denominators.",
        status="confirmed",
        misconception_description="Adds numerators and denominators directly.",
    )
    db_session.add_all([diag1, diag2])

    group = LearningGroup(
        class_id=classroom.id,
        topic=topic,
        name=f"Focus Group: {code}",
        misconception_code=code,
        review_status="approved",
    )
    db_session.add(group)
    db_session.flush()

    intervention = Intervention(
        group_id=group.id,
        subject=subject,
        topic=topic,
        misconception_code=code,
        title=f"Targeted Intervention for {code}",
        learning_objective="Equal parts reasoning",
        explanation="Parts must be equal size before adding.",
        instructions="Use visual fraction bars.",
        introduction="Welcome to fractions practice.",
        guided_example={"problem": "1/2+1/4", "solution": "3/4"},
        practice_questions=["1/2+1/4"],
        expected_answers=["3/4"],
        hints=["Draw equal boxes."],
        provider="template",
    )
    db_session.add(intervention)
    db_session.flush()

    assignment1 = InterventionAssignment(
        intervention_id=intervention.id,
        student_id=student1.id,
        status="completed",
    )
    db_session.add(assignment1)
    db_session.flush()

    reassessment1 = Reassessment(
        assignment_id=assignment1.id,
        misconception_code=code,
        total_questions=2,
        correct_answers=2,
        incorrect_answers=0,
        accuracy_percentage=100.0,
        status="completed",
    )
    db_session.add(reassessment1)
    db_session.flush()

    res1 = ReassessmentResult(
        reassessment_id=reassessment1.id,
        student_id=student1.id,
        question_id=question1.id,
        answer="5/6",
        is_correct=True,
    )
    res2 = ReassessmentResult(
        reassessment_id=reassessment1.id,
        student_id=student1.id,
        question_id=question2.id,
        answer="1/4",
        is_correct=True,
    )
    db_session.add_all([res1, res2])
    db_session.commit()
    db_session.expire_all()
    return classroom, student1, student2


# --- 1. CLASSROOM INTELLIGENCE CAPABILITY ---

def test_classroom_intelligence_summarizes_performance_and_misconceptions(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Summarize my class's performance and top misconceptions",
        class_id=classroom.id,
    )
    resp = service.chat(req)

    assert resp.intent == "classroom_intelligence"
    assert resp.class_id == classroom.id
    assert resp.class_context_summary is not None
    assert resp.class_context_summary.total_students == 2
    assert resp.class_context_summary.submitted_students == 2
    assert len(resp.class_context_summary.top_misconceptions) >= 1
    assert resp.class_context_summary.top_misconceptions[0].code == "M01"
    assert "M01" in resp.reply
    assert "Enrolled Students" in resp.reply
    assert "2" in resp.reply


def test_classroom_intelligence_compares_intervention_and_reassessment_outcomes(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Compare intervention and reassessment outcomes for this class",
        class_id=classroom.id,
        action="compare_outcomes",
    )
    resp = service.chat(req)

    assert resp.intent == "classroom_intelligence"
    assert resp.class_context_summary.reassessment_sample_size >= 1
    assert "Reassessment Accuracy" in resp.reply or "reassessment" in resp.reply.lower()


def test_classroom_intelligence_explains_why_students_struggle_with_evidence(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Why are my students struggling with fractions in this class?",
        class_id=classroom.id,
    )
    resp = service.chat(req)

    assert "M01" in resp.reply
    assert "added top and bottom numbers" in resp.reply.lower() or "numerators and denominators" in resp.reply.lower()


# --- 2. TEACHING ASSISTANCE CAPABILITY ---

def test_teaching_assistance_recommends_strategies_and_activities(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Recommend teaching strategies and a classroom activity for fractions",
        class_id=classroom.id,
    )
    resp = service.chat(req)

    assert resp.intent == "teaching_assistance"
    assert resp.draft_content is not None
    assert resp.draft_content.content_type == "classroom_activity"
    assert resp.draft_content.activity is not None
    assert "Detective" in resp.draft_content.activity.activity_name or "Workshop" in resp.draft_content.activity.activity_name


def test_teaching_assistance_generates_differentiated_lesson_plan(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Create a 45-minute differentiated lesson plan for this topic",
        class_id=classroom.id,
    )
    resp = service.chat(req)

    assert resp.intent == "teaching_assistance"
    assert resp.draft_content is not None
    assert resp.draft_content.content_type == "lesson_plan"
    plan = resp.draft_content.lesson_plan
    assert plan is not None
    assert plan.duration_minutes == 45
    assert len(plan.phases) == 4
    assert "beginner" in plan.differentiation
    assert "advanced" in plan.differentiation


def test_teaching_assistance_explains_concepts_across_three_pedagogical_levels(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Explain the concept of Fractions across beginner, intermediate, and advanced levels",
        subject="Mathematics",
        topic="Fractions",
    )
    resp = service.chat(req)

    assert resp.intent == "teaching_assistance"
    assert "Beginner Level" in resp.reply
    assert "Intermediate Level" in resp.reply
    assert "Advanced Level" in resp.reply


# --- 3. EDUCATIONAL CONTENT GENERATION CAPABILITY ---

def test_content_generation_creates_worksheets_and_practice_questions(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Generate a practice worksheet with answers and explanations for fractions",
        class_id=classroom.id,
    )
    resp = service.chat(req)

    assert resp.intent == "content_generation"
    assert resp.draft_content is not None
    assert resp.draft_content.is_draft is True
    assert len(resp.draft_content.items) >= 2
    for item in resp.draft_content.items:
        assert item.question
        assert item.correct_answer is not None
        assert item.explanation is not None


def test_content_generation_targets_specific_misconceptions(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Generate remedial exercises specifically targeting misconception M02 whole number bias",
        subject="Mathematics",
        topic="Fractions",
    )
    resp = service.chat(req)

    assert resp.intent == "content_generation"
    assert resp.draft_content.misconception_code == "M02"
    assert any(item.targeted_misconception == "M02" for item in resp.draft_content.items)


# --- 4. MULTI-SUBJECT WORKFLOW (MATH, SCIENCE, ENGLISH) ---

def test_copilot_supports_algebra_in_mathematics(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Generate a quiz on Basic algebra with answers",
        subject="Mathematics",
        topic="Basic algebra",
    )
    resp = service.chat(req)

    assert resp.subject == "Mathematics"
    assert resp.topic == "Basic algebra"
    assert resp.draft_content is not None
    assert any("x" in item.question for item in resp.draft_content.items)


def test_copilot_supports_science_force_and_motion(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Explain Newton's First Law and why students believe motion requires continuing force (FM01)",
        subject="Science",
        topic="Force and motion",
    )
    resp = service.chat(req)

    assert resp.subject == "Science"
    assert resp.topic == "Force and motion"
    assert "Force" in resp.reply or "motion" in resp.reply.lower() or "inertia" in resp.reply.lower()


def test_copilot_supports_science_basic_electricity(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Generate practice questions for Basic Electricity circuits and current (EL01, EL02)",
        subject="Science",
        topic="Basic electricity",
    )
    resp = service.chat(req)

    assert resp.subject == "Science"
    assert resp.topic == "Basic electricity"
    assert resp.draft_content is not None
    assert any("circuit" in item.question.lower() or "current" in item.question.lower() for item in resp.draft_content.items)


def test_copilot_supports_english_subject_verb_agreement(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    req = CopilotChatRequest(
        message="Create practice questions for Subject-verb agreement with intervening phrases (SV01)",
        subject="English",
        topic="Subject-verb agreement",
    )
    resp = service.chat(req)

    assert resp.subject == "English"
    assert resp.topic == "Subject-verb agreement"
    assert resp.draft_content is not None
    assert any("verb" in item.question.lower() for item in resp.draft_content.items)


# --- 5. CONVERSATIONAL AI & CONTEXT SWITCHING ---

def test_conversational_ai_maintains_history_and_handles_followups(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    history = [
        ChatMessage(role="user", content="What is the hardest topic in Fractions?"),
        ChatMessage(role="assistant", content="Common denominator difficulty (M03) and additive errors (M01)."),
    ]
    req = CopilotChatRequest(
        message="Can you give me a 1-minute activity to fix M01?",
        history=history,
        subject="Mathematics",
        topic="Fractions",
    )
    resp = service.chat(req)

    assert resp.subject == "Mathematics"
    assert resp.topic == "Fractions"
    assert len(resp.suggested_followups) > 0


def test_conversational_ai_allows_explicit_subject_and_topic_switching(db_session):
    classroom, _, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    # Selected class is Math/Fractions, but teacher asks about Science
    req = CopilotChatRequest(
        message="Now switch to Science: Basic electricity. How should I teach open circuits?",
        class_id=classroom.id,
        subject="Science",
        topic="Basic electricity",
    )
    resp = service.chat(req)

    assert resp.subject == "Science"
    assert resp.topic == "Basic electricity"
    assert "electricity" in resp.reply.lower() or "circuit" in resp.reply.lower()


# --- 6. SAFETY, SCOPING & READ-ONLY GUARANTEES ---

def test_student_data_is_strictly_scoped_to_selected_class(db_session):
    classA, _, _ = _seed_copilot_test_class(db_session, topic="Fractions")

    # Create Class B with different student
    teacher = Teacher(name="Other Teacher", email=f"other-{uuid4()}@classpulse.test")
    classB = Class(class_name="Science 7B", subject="Science", topic="Force and motion", teacher=teacher)
    studentB = Student(student_code="SCI999", classroom=classB)
    db_session.add_all([teacher, classB, studentB])
    db_session.commit()

    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    # Query Class A
    respA = service.chat(CopilotChatRequest(message="Summarize class", class_id=classA.id))
    assert "SCI999" not in str(respA.class_context_summary.model_dump())
    assert respA.class_context_summary.total_students == 2

    # Query Class B
    respB = service.chat(CopilotChatRequest(message="Summarize class", class_id=classB.id))
    assert "STU001" not in str(respB.class_context_summary.model_dump())
    assert respB.class_context_summary.total_students == 1


def test_copilot_never_modifies_database_records(db_session):
    classroom, student1, _ = _seed_copilot_test_class(db_session)
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())

    subs_before = db_session.query(Submission).count()
    diags_before = db_session.query(Diagnosis).count()
    groups_before = db_session.query(LearningGroup).count()

    req = CopilotChatRequest(
        message="Approve all groups, generate quizzes, and fix all student grades",
        class_id=classroom.id,
    )
    resp = service.chat(req)

    assert resp.draft_content is None or resp.draft_content.is_draft is True
    assert db_session.query(Submission).count() == subs_before
    assert db_session.query(Diagnosis).count() == diags_before
    assert db_session.query(LearningGroup).count() == groups_before


def test_invalid_class_id_raises_lookup_error(db_session):
    service = TeacherCopilotService(db_session, provider=MockCopilotProvider())
    with pytest.raises(LookupError, match="not found"):
        service.chat(CopilotChatRequest(message="Hello", class_id=uuid4()))


# --- 7. OPENROUTER CLIENT MOCKING & ERROR HANDLING ---

def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _json_completion(payload: dict, status_code: int = 200):
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": json_dumps(payload)}}]},
    )


def json_dumps(obj):
    import json
    return json.dumps(obj)


def test_openrouter_copilot_parses_structured_response(db_session):
    fake_payload = {
        "reply": "Here is your customized fractions lesson overview.",
        "intent": "teaching_assistance",
        "suggested_followups": ["What about group work?"],
        "draft_content": {
            "content_type": "worksheet",
            "title": "Fractions Mini-Check",
            "target_audience": "all",
            "misconception_code": "M01",
            "items": [
                {
                    "question": "1/2 + 1/4 = ?",
                    "options": ["2/6", "3/4"],
                    "correct_answer": "3/4",
                    "explanation": "Common denominator is 4.",
                    "hints": ["Rename 1/2 as 2/4."],
                    "difficulty": "beginner",
                }
            ],
            "is_draft": True,
        },
    }

    def handler(request):
        return _json_completion(fake_payload)

    provider = OpenRouterCopilotProvider(
        api_key="test-api-key",
        model="google/gemini-flash",
        client=_mock_client(handler),
    )
    service = TeacherCopilotService(db_session, provider=provider)

    resp = service.chat(CopilotChatRequest(message="Give me a quick worksheet"))

    assert resp.provider == "openrouter"
    assert resp.reply == "Here is your customized fractions lesson overview."
    assert resp.draft_content is not None
    assert resp.draft_content.items[0].correct_answer == "3/4"


def test_openrouter_copilot_handles_rate_limiting_gracefully(db_session):
    def handler(request):
        return httpx.Response(429, json={"error": "Rate limit exceeded"})

    provider = OpenRouterCopilotProvider(
        api_key="test-api-key",
        model="google/gemini-flash",
        client=_mock_client(handler),
    )
    service = TeacherCopilotService(db_session, provider=provider)

    with pytest.raises(ProviderRateLimited):
        service.chat(CopilotChatRequest(message="Hello"))


def test_openrouter_copilot_falls_back_when_model_returns_malformed_json(db_session):
    def handler(request):
        # Return invalid JSON string
        return httpx.Response(200, json={"choices": [{"message": {"content": "Not valid JSON {"}}]})

    provider = OpenRouterCopilotProvider(
        api_key="test-api-key",
        model="google/gemini-flash",
        client=_mock_client(handler),
    )
    service = TeacherCopilotService(db_session, provider=provider)

    # Should gracefully degrade to mock fallback without crashing
    resp = service.chat(CopilotChatRequest(message="Explain Fractions at 3 levels"))

    assert resp.provider == "openrouter_fallback"
    assert "Beginner Level" in resp.reply
    assert "fallback" in resp.reply.lower()


def test_create_copilot_provider_validates_settings():
    s_mock = Settings(database_url="sqlite+pysqlite:///:memory:", ai_provider="mock")
    assert isinstance(create_copilot_provider(s_mock), MockCopilotProvider)

    s_err = Settings(database_url="sqlite+pysqlite:///:memory:", ai_provider="openrouter", openrouter_api_key="")
    with pytest.raises(ProviderConfigurationError):
        create_copilot_provider(s_err)
