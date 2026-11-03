"""Gemini transport and provider selection use fake keys and controlled HTTP."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.schemas.copilot import CopilotChatRequest
from app.services.copilot_provider import create_copilot_provider
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
    create_diagnosis_provider,
)


def settings(**updates):
    return Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        ai_provider="gemini",
        gemini_api_key="fake-gemini-key",
        gemini_model="gemini-3.1-flash-lite",
        **updates,
    )


def completion(payload):
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": json.dumps(payload)}]},
                "finishReason": "STOP",
            }
        ]
    }


def test_settings_accept_gemini_and_keep_its_model_separate():
    config = settings()
    assert config.ai_provider == "gemini"
    assert config.gemini_model == "gemini-3.1-flash-lite"


def test_native_gemini_transport_uses_header_key_and_json_generation():
    from app.services.gemini_client import GeminiChatClient

    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(
            200, json=completion({"reply": "Use sixths before adding."})
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = GeminiChatClient(
            api_key="fake-gemini-key", model="gemini-3.1-flash-lite", client=http
        )
        result = json.loads(
            client.complete_json(prompt="Explain fractions as JSON.", temperature=0.2)
        )
    assert result["reply"] == "Use sixths before adding."
    request = captured[0]
    assert (
        str(request.url)
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"
    )
    assert request.headers["x-goog-api-key"] == "fake-gemini-key"
    assert "fake-gemini-key" not in str(request.url)
    payload = json.loads(request.content)
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert payload["contents"][0]["parts"][0]["text"] == "Explain fractions as JSON."


@pytest.mark.parametrize(
    "status,exception",
    [
        (400, ProviderError),
        (401, ProviderConfigurationError),
        (403, ProviderConfigurationError),
        (429, ProviderRateLimited),
        (503, ProviderError),
    ],
)
def test_upstream_failures_do_not_expose_key_or_provider_body(status, exception):
    from app.services.gemini_client import GeminiChatClient

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status,
                json={"error": {"message": "sensitive-provider-body fake-gemini-key"}},
            )
        )
    ) as http:
        client = GeminiChatClient(
            api_key="fake-gemini-key", model="gemini-3.1-flash-lite", client=http
        )
        with pytest.raises(exception) as error:
            client.complete_json(prompt="Return JSON.", temperature=0)
    assert "fake-gemini-key" not in str(error.value)
    assert "sensitive-provider-body" not in str(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"candidates": []},
        {"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]},
        {"bad": "shape"},
    ],
)
def test_empty_or_blocked_generation_is_not_a_success(payload):
    from app.services.gemini_client import GeminiChatClient

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as http:
        with pytest.raises(ProviderError):
            GeminiChatClient(
                api_key="fake", model="gemini-3.1-flash-lite", client=http
            ).complete_json(prompt="Return JSON.", temperature=0)


def test_teacher_copilot_uses_gemini_and_labels_live_response():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=completion(
                    {
                        "reply": "Use a number line to compare fractions.",
                        "intent": "teaching_assistance",
                        "suggested_followups": [],
                    }
                ),
            )
        )
    ) as http:
        provider = create_copilot_provider(settings(), client=http)
        response = provider.generate(CopilotChatRequest(message="Explain fractions"))
    assert response.provider == "gemini"
    assert response.model_version == "gemini-3.1-flash-lite"
    assert response.reply == "Use a number line to compare fractions."


def test_teacher_fallback_is_explicitly_labeled_gemini():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, json={"error": {"message": "private"}})
        )
    ) as http:
        provider = create_copilot_provider(settings(), client=http)
        response = provider.generate(CopilotChatRequest(message="Explain fractions"))
    assert response.provider == "gemini_fallback"
    assert "private" not in response.reply


def test_diagnosis_factory_uses_gemini_and_preserves_provenance():
    data = {
        "misconception_code": "M01",
        "confidence": 0.8,
        "evidence": "I added both",
        "needs_followup": False,
    }
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=completion(data))
        )
    ) as http:
        provider = create_diagnosis_provider(settings(), client=http)
        output = provider.diagnose(
            question="1/2 + 1/3?",
            answer="2/5",
            explanation="I added both",
            correct_answer="5/6",
        )
    assert output.provider == "gemini"
    assert output.model_version == "gemini-3.1-flash-lite"


def test_quiz_tutor_and_lesson_use_gemini(monkeypatch):
    from app.services import quiz_tutor
    from app.services.gemini_client import GeminiChatClient

    monkeypatch.setattr(quiz_tutor, "get_settings", lambda: settings())

    def complete(self, *, prompt, temperature):
        if "five-minute teacher lesson" in prompt:
            return json.dumps(
                {
                    "text": "Use fraction strips, then check the approved repair question."
                }
            )
        return json.dumps(
            {
                "error_type": "procedure",
                "evidence": "I added both",
                "reply": "Rename both fractions in sixths first.",
            }
        )

    monkeypatch.setattr(GeminiChatClient, "complete_json", complete)
    q = {
        "text": "1/2 + 1/3?",
        "options": ["2/5", "5/6"],
        "correct_option": 1,
        "explanation": "Use sixths.",
        "concept": "Fractions",
    }
    response = quiz_tutor.tutor_feedback(
        q, 0, [{"role": "student", "content": "I added both"}], "en"
    )
    assert response["provider"] == "gemini"
    assert response["model"] == "gemini-3.1-flash-lite"
    assert response["error_type"] == "procedure"
    report = {
        "submitted_students": 1,
        "questions": [
            {
                **q,
                "id": "q1",
                "ordinal": 1,
                "answered_students": 1,
                "correct_students": 0,
                "reflected_students": 1,
                "uncertain_students": 0,
                "themes": [],
            }
        ],
    }
    assert quiz_tutor.lesson_suggestion(report)["provider"] == "gemini"


def test_gemini_missing_key_fails_configuration_without_network():
    config = Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        ai_provider="gemini",
        gemini_api_key="",
    )
    with pytest.raises(ProviderConfigurationError, match="GEMINI_API_KEY"):
        create_copilot_provider(config)


def test_intervention_personalization_uses_gemini_without_changing_keys():
    from app.services.intervention_provider import create_intervention_provider

    result = {
        "explanation": "Use a common denominator.",
        "instructions": "Compare fraction strips.",
        "introduction": "Let us review fractions.",
        "hints": ["Use sixths."],
    }
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=completion(result))
        )
    ) as http:
        provider = create_intervention_provider(settings(), client=http)
        output = provider.personalize(
            subject="Mathematics",
            topic="Fractions",
            misconception_code="M01",
            taxonomy_description="Adds denominators",
            learning_objective="Add fractions",
            learning_gap=["I added both"],
            explanation="Use sixths.",
            instructions="Rename first.",
            introduction="Hello",
            hints=["Use sixths."],
        )
    assert provider.name == "gemini"
    assert output.explanation == "Use a common denominator."
    assert not hasattr(output, "correct_answer")
