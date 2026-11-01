import time

import httpx
import pytest

from app.core.config import Settings
from app.models import Class, Diagnosis, Question, Student, Submission, Teacher
from app.schemas.diagnosis import (
    DiagnosisResult,
    validate_evidence_quotes,
)
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
    RuleBasedDiagnosisProvider,
    create_diagnosis_provider,
)
from app.services.llm_service import OpenRouterDiagnosisProvider
from app.services.diagnosis_service import DiagnosisService


def test_mock_provider_is_default_without_api_key():
    settings = Settings(database_url="sqlite+pysqlite:///:memory:")

    provider = create_diagnosis_provider(settings)

    assert isinstance(provider, RuleBasedDiagnosisProvider)
    assert provider.name == "mock"


def test_rule_based_provider_diagnoses_hindi_explanation_with_verbatim_quote():
    result = RuleBasedDiagnosisProvider().diagnose(
        question="Calculate 1/2 + 1/3.",
        answer="2/5",
        explanation="मैंने अंश और हर जोड़ दिए।",
        correct_answer="5/6",
    )

    assert result.misconception_code == "M01"
    assert result.evidence == "मैंने अंश और हर जोड़ दिए।"
    validate_evidence_quotes(result, "2/5", "मैंने अंश और हर जोड़ दिए।")


def test_hindi_submission_is_diagnosed_and_persisted(db_session):
    teacher = Teacher(name="Teacher", email="hindi@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    student = Student(student_code="HI001", classroom=classroom)
    question = Question(
        topic="Fractions",
        question_text="Calculate 1/2 + 1/3.",
        correct_answer="5/6",
    )
    submission = Submission(
        student=student,
        question=question,
        answer="2/5",
        explanation="मैंने अंश और हर जोड़ दिए।",
    )
    db_session.add(submission)
    db_session.flush()

    outcome = DiagnosisService(
        db_session,
        provider=RuleBasedDiagnosisProvider(),
    ).diagnose_class(classroom.id)

    diagnosis = db_session.query(Diagnosis).one()
    assert outcome.diagnosed == 1
    assert diagnosis.misconception_code == "M01"
    assert diagnosis.evidence == "मैंने अंश और हर जोड़ दिए।"
    assert diagnosis.provider == "mock"


def test_rule_based_provider_identifies_clear_whole_number_bias():
    result = RuleBasedDiagnosisProvider().diagnose(
        question="Which is larger, 1/4 or 1/8?",
        answer="1/8",
        explanation="Eight is bigger than four.",
        correct_answer="1/4",
    )

    assert result.misconception_code == "M02"
    assert result.evidence == "Eight is bigger than four."


def test_wrong_final_answer_without_reasoning_is_not_a_misconception():
    result = RuleBasedDiagnosisProvider().diagnose(
        question="Calculate 1/2 + 1/3.",
        answer="2/5",
        explanation=None,
        correct_answer="5/6",
    )

    assert result.misconception_code == "M06"
    assert result.needs_followup is True


def test_evidence_quotes_must_appear_in_answer_or_explanation():
    result = DiagnosisResult(
        misconception_code="M01",
        confidence=0.9,
        evidence="I added the numerator and denominator.",
    )

    with pytest.raises(ValueError, match="evidence quote"):
        validate_evidence_quotes(result, "2/5", "I added the top numbers.")


def test_empty_evidence_rejected_for_misconception_labels():
    result = DiagnosisResult(
        misconception_code="M01",
        confidence=0.9,
        evidence="",
    )

    with pytest.raises(ValueError, match="evidence quote must not be empty"):
        validate_evidence_quotes(result, "2/5", "I added the top numbers.")

    # M06 and CORRECT are allowed to have empty evidence quotes
    m06_result = DiagnosisResult(
        misconception_code="M06",
        confidence=0.3,
        evidence="",
    )
    validate_evidence_quotes(m06_result, "", "")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "misconception_code": "M99",
                "confidence": 0.9,
                "evidence": "verbatim",
            },
            "misconception_code",
        ),
        (
            {
                "misconception_code": "M01",
                "confidence": 1.1,
                "evidence": "verbatim",
            },
            "confidence",
        ),
    ],
)
def test_diagnosis_schema_rejects_invalid_label_or_confidence(kwargs, message):
    with pytest.raises(ValueError, match=message):
        DiagnosisResult(**kwargs)


def test_rule_based_provider_distinguishes_procedural_slip_and_uncertainty():
    provider = RuleBasedDiagnosisProvider()
    procedural = provider.diagnose(
        question="Add 1/3 + 1/6.",
        answer="3/6",
        explanation="I changed one fraction to sixths, then added but may have made a calculation mistake.",
        correct_answer="1/2",
    )
    uncertain = provider.diagnose(
        question="Compare 2/3 and 3/4.",
        answer="",
        explanation="I don't know.",
        correct_answer="3/4",
    )

    assert procedural.misconception_code == "M05"
    assert procedural.needs_followup is False
    assert uncertain.misconception_code == "M06"
    assert uncertain.needs_followup is True


def _mock_openrouter_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _completion(content: str, *, status_code: int = 200):
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": content}}]},
    )


def test_openrouter_provider_requires_api_key():
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        ai_provider="openrouter",
        openrouter_model="provider/model",
    )

    with pytest.raises(ProviderConfigurationError, match="OPENROUTER_API_KEY"):
        create_diagnosis_provider(settings)


def test_openrouter_provider_accepts_valid_configuration_and_parses_response():
    content = (
        '{"misconception_code":"M01","confidence":0.94,'
        '"evidence":"I added the top numbers and the bottom numbers.",'
        '"needs_followup":false,"followup_question":null}'
    )
    requests = []

    def handler(request):
        requests.append(request)
        return _completion(content)

    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        ai_provider="openrouter",
        openrouter_api_key="test-key-not-real",
        openrouter_model="provider/model",
        openrouter_base_url="https://openrouter.example/api/v1",
    )
    provider = create_diagnosis_provider(
        settings,
        client=_mock_openrouter_client(handler),
    )
    result = provider.diagnose(
        question="Calculate 1/2 + 1/3.",
        answer="2/5",
        explanation="I added the top numbers and the bottom numbers.",
        correct_answer="5/6",
    )

    assert result.provider == "openrouter"
    assert result.model_version == "provider/model"
    assert "test-key-not-real" not in result.model_dump_json()
    assert requests[0].url.path == "/api/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer test-key-not-real"
    assert requests[0].read().find(b'"model":"provider/model"') != -1


def test_openrouter_rejects_invalid_chat_completion_response():
    provider = OpenRouterDiagnosisProvider(
        api_key="test-key-not-real",
        model="provider/model",
        client=_mock_openrouter_client(
            lambda _request: httpx.Response(200, json={"choices": []})
        ),
    )

    with pytest.raises(ProviderError, match="invalid chat completion"):
        provider.diagnose(
            question="Calculate 1/2 + 1/3.",
            answer="2/5",
            explanation="I added the top and bottom numbers.",
            correct_answer="5/6",
        )


def test_openrouter_rejects_invalid_structured_diagnosis():
    provider = OpenRouterDiagnosisProvider(
        api_key="test-key-not-real",
        model="provider/model",
        client=_mock_openrouter_client(
            lambda _request: _completion(
                '{"misconception_code":"M99","confidence":2,"evidence":"invented"}'
            )
        ),
    )

    with pytest.raises(ProviderError, match="invalid diagnosis response"):
        provider.diagnose(
            question="Calculate 1/2 + 1/3.",
            answer="2/5",
            explanation="I added the top and bottom numbers.",
            correct_answer="5/6",
        )


def test_openrouter_identifies_rate_limit():
    provider = OpenRouterDiagnosisProvider(
        api_key="test-key-not-real",
        model="provider/model",
        client=_mock_openrouter_client(
            lambda _request: httpx.Response(429)
        ),
    )

    with pytest.raises(ProviderRateLimited, match="OpenRouter rate limit"):
        provider.diagnose(
            question="Calculate 1/2 + 1/3.",
            answer="2/5",
            explanation="I added the top and bottom numbers.",
            correct_answer="5/6",
        )


def test_openrouter_invalid_credentials_are_reported_without_echoing_key():
    provider = OpenRouterDiagnosisProvider(
        api_key="test-key-not-real",
        model="provider/model",
        client=_mock_openrouter_client(
            lambda _request: httpx.Response(401)
        ),
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="authentication failed; check OPENROUTER_API_KEY",
    ) as error:
        provider.diagnose(
            question="Calculate 1/2 + 1/3.",
            answer="2/5",
            explanation="I added the top and bottom numbers.",
            correct_answer="5/6",
        )
    assert "test-key-not-real" not in str(error.value)


def test_openrouter_timeout_is_explicit():
    def handler(_request):
        raise httpx.ReadTimeout("timeout")

    provider = OpenRouterDiagnosisProvider(
        api_key="test-key-not-real",
        model="provider/model",
        client=_mock_openrouter_client(handler),
    )

    with pytest.raises(ProviderError, match="request timed out"):
        provider.diagnose(
            question="Calculate 1/2 + 1/3.",
            answer="2/5",
            explanation="I added the top and bottom numbers.",
            correct_answer="5/6",
        )


def test_openrouter_errors_do_not_fall_back_to_mock():
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        ai_provider="openrouter",
        openrouter_api_key="test-key-not-real",
        openrouter_model="provider/model",
    )
    provider = create_diagnosis_provider(
        settings,
        client=_mock_openrouter_client(
            lambda _request: httpx.Response(503)
        ),
    )

    with pytest.raises(ProviderError, match="HTTP 503"):
        provider.diagnose(
            question="Calculate 1/2 + 1/3.",
            answer="2/5",
            explanation="I added the top and bottom numbers.",
            correct_answer="5/6",
        )
    assert provider.name == "openrouter"


def test_mock_mode_works_without_openrouter_credentials():
    settings = Settings(database_url="sqlite+pysqlite:///:memory:")
    provider = create_diagnosis_provider(settings)

    assert isinstance(provider, RuleBasedDiagnosisProvider)
    assert provider.name == "mock"


def test_diagnosis_service_limits_batch_to_twenty_and_reports_remaining(
    db_session,
):
    teacher = Teacher(name="Teacher", email="batch@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    question = Question(
        topic="Fractions",
        question_text="Calculate 1/2 + 1/3.",
        correct_answer="5/6",
    )
    db_session.add_all([teacher, question])
    db_session.flush()
    for index in range(21):
        student = Student(
            class_id=classroom.id,
            student_code=f"S{index:03d}",
        )
        db_session.add(student)
        db_session.flush()
        db_session.add(
            Submission(
                student_id=student.id,
                question_id=question.id,
                answer="2/5",
                explanation="I added the top and bottom numbers.",
            )
        )
    db_session.flush()

    result = DiagnosisService(
        db_session,
        provider=RuleBasedDiagnosisProvider(),
        batch_timeout_seconds=10,
    ).diagnose_class(classroom.id)

    assert result.diagnosed == 20
    assert result.remaining_pending == 1
    assert db_session.query(Diagnosis).count() == 20


def test_diagnosis_service_returns_after_provider_batch_timeout(db_session):
    teacher = Teacher(name="Teacher", email="timeout@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    student = Student(student_code="S001", classroom=classroom)
    question = Question(
        topic="Fractions",
        question_text="Calculate 1/2 + 1/3.",
        correct_answer="5/6",
    )
    submission = Submission(
        student=student,
        question=question,
        answer="2/5",
        explanation="I added the top and bottom numbers.",
    )
    db_session.add(submission)
    db_session.flush()

    class SlowProvider:
        name = "mock"
        model_version = "slow-test"

        def diagnose(self, **_kwargs):
            time.sleep(0.1)
            return RuleBasedDiagnosisProvider().diagnose(
                question=question.question_text,
                answer=submission.answer,
                explanation=submission.explanation,
                correct_answer=question.correct_answer,
            )

    started = time.monotonic()
    result = DiagnosisService(
        db_session,
        provider=SlowProvider(),
        batch_timeout_seconds=0.01,
    ).diagnose_class(classroom.id)

    assert time.monotonic() - started < 0.08
    assert result.timed_out == 1
    assert result.diagnosed == 0
    assert db_session.query(Diagnosis).count() == 0
