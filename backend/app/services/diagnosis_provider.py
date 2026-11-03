from typing import Protocol

from app.core.config import Settings
from app.question_catalog import QUESTION_CATALOG
from app.schemas.diagnosis import DiagnosisResult
from app.subject_taxonomy import FOLLOW_UP_CODE, get_taxonomy


class ProviderError(RuntimeError):
    pass


class ProviderConfigurationError(ProviderError):
    pass


class ProviderRateLimited(ProviderError):
    pass


class DiagnosisProvider(Protocol):
    name: str
    model_version: str

    def diagnose(
        self,
        *,
        subject: str = "Mathematics",
        topic: str = "Fractions",
        question: str,
        answer: str | None,
        explanation: str | None,
        correct_answer: str,
        expected_approach: str | None = None,
    ) -> DiagnosisResult: ...


class RuleBasedDiagnosisProvider:
    name = "mock"
    model_version = "rules-v1"

    def diagnose(
        self,
        *,
        subject: str = "Mathematics",
        topic: str = "Fractions",
        question: str,
        answer: str | None,
        explanation: str | None,
        correct_answer: str,
        expected_approach: str | None = None,
    ) -> DiagnosisResult:
        del expected_approach
        if (subject, topic) != ("Mathematics", "Fractions"):
            return DiagnosisResult(
                misconception_code=FOLLOW_UP_CODE,
                confidence=0.3,
                evidence=(explanation or answer or "")[:1000],
                misconception_description="Mock mode does not infer this subject's misconceptions.",
                misunderstanding_explanation=(
                    "This response needs review by the configured diagnosis provider."
                ),
                suggested_intervention="Ask the learner to explain their reasoning.",
                needs_followup=True,
                followup_question="Can you explain how you decided on your answer?",
                provider=self.name,
                model_version=self.model_version,
            )
        response_text = explanation or ""
        normalized = response_text.casefold()
        answer_value = (answer or "").strip()
        acceptable = {correct_answer.strip().casefold()}
        catalog_entry = next(
            (q for q in QUESTION_CATALOG.values() if q.question_text == question),
            None,
        )
        if catalog_entry:
            acceptable.update(a.strip().casefold() for a in catalog_entry.accepted_answers)
        correct = answer_value.casefold() in acceptable
        code = "M06"
        confidence = 0.3
        evidence = response_text
        followup = (
            "Can you explain your steps or show the fractions on a number line?"
        )

        direct_addition = any(
            phrase in normalized
            for phrase in (
                "added the top",
                "added the numerator",
                "added the numerators",
                "top numbers and the bottom",
                "numerators and denominators",
                "अंश और हर जोड़",
                "अंश और हर को जोड़",
            )
        )
        whole_number_bias = any(
            phrase in normalized
            for phrase in (
                "eight is bigger than four",
                "denominator is bigger",
                "larger denominator",
                "bigger denominator",
                "हर बड़ा",
                "हर बड़ा है",
            )
        )
        equivalence_error = any(
            phrase in normalized
            for phrase in (
                "numbers are different",
                "not equivalent",
                "not the same",
                "अलग-अलग संख्या",
                "बराबर नहीं",
            )
        )
        common_denominator_error = any(
            phrase in normalized
            for phrase in (
                "without a common denominator",
                "didn't use a common denominator",
                "did not use a common denominator",
                "didn't make a common denominator",
            )
        )
        sound_method = any(
            phrase in normalized
            for phrase in (
                "changed",
                "common denominator",
                "equivalent fraction",
                "denominator 12",
                "sixths",
            )
        )
        arithmetic_slip = any(
            phrase in normalized
            for phrase in (
                "calculation mistake",
                "arithmetic mistake",
                "arithmetic error",
                "added incorrectly",
                "may have miscalculated",
            )
        )

        if not answer_value and not response_text.strip():
            pass
        elif direct_addition:
            code, confidence, followup = (
                "M01",
                0.94,
                "Draw both fractions. How many equal-sized parts make the whole?",
            )
        elif whole_number_bias:
            code, confidence, followup = (
                "M02",
                0.93,
                "Which is larger: one slice out of 4 or one out of 8? Why?",
            )
        elif equivalence_error and "equivalent" in question.casefold():
            code, confidence, followup = (
                "M04",
                0.88,
                "Show both fractions on the same number line.",
            )
        elif common_denominator_error:
            code, confidence, followup = (
                "M03",
                0.84,
                "Rewrite both fractions with a common denominator.",
            )
        elif sound_method and arithmetic_slip and not correct:
            code, confidence, followup = (
                "M05",
                0.82,
                "Repeat the arithmetic while keeping the same fraction method.",
            )
        elif correct and response_text.strip():
            code, confidence, evidence, followup = (
                "CORRECT",
                0.9,
                response_text,
                None,
            )

        return DiagnosisResult(
            misconception_code=code,
            confidence=confidence,
            evidence=evidence,
            misconception_description=next(
                (
                    item.description
                    for item in get_taxonomy(subject, topic)
                    if item.code == code
                ),
                "",
            ),
            misunderstanding_explanation=(
                "The response suggests this reasoning pattern."
                if code not in {"M06", "CORRECT"}
                else ""
            ),
            suggested_intervention=(
                "Use a targeted fractions explanation and guided practice."
                if code not in {"M06", "CORRECT"}
                else ""
            ),
            needs_followup=code == "M06" or confidence < 0.75,
            followup_question=followup,
            provider=self.name,
            model_version=self.model_version,
        )


def create_diagnosis_provider(
    settings: Settings,
    *,
    client=None,
) -> DiagnosisProvider:
    if settings.ai_provider == "mock":
        return RuleBasedDiagnosisProvider()
    if settings.ai_provider == "gemini":
        from app.services.gemini_client import GeminiChatClient
        from app.services.llm_service import OpenRouterDiagnosisProvider
        return OpenRouterDiagnosisProvider(
            api_key="", model=settings.gemini_model,
            chat_client=GeminiChatClient.from_settings(settings, client=client),
            provider_name="gemini",
        )
    if settings.ai_provider == "openrouter":
        from app.services.llm_service import OpenRouterDiagnosisProvider

        return OpenRouterDiagnosisProvider(
            api_key=settings.openrouter_api_key or "",
            model=settings.openrouter_model or "",
            base_url=settings.openrouter_base_url,
            timeout_seconds=settings.openrouter_timeout_seconds,
            client=client,
        )
    raise ValueError(f"Unsupported AI_PROVIDER: {settings.ai_provider}")
