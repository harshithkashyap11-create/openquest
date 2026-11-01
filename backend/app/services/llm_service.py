from pydantic import ValidationError

from app.schemas.diagnosis import DiagnosisResult
from app.services.diagnosis_prompt import build_diagnosis_prompt
from app.services.diagnosis_provider import ProviderError
from app.services.openrouter_client import OpenRouterChatClient


class OpenRouterDiagnosisProvider:
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 20,
        client=None,
    ) -> None:
        self.client = OpenRouterChatClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        self.model_version = model

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
        prompt = build_diagnosis_prompt(
            subject=subject,
            topic=topic,
            question=question,
            correct_answer=correct_answer,
            expected_approach=expected_approach,
            answer=answer,
            explanation=explanation,
        )
        content = self.client.complete_json(prompt=prompt, temperature=0)
        try:
            result = DiagnosisResult.model_validate_json(content)
        except ValidationError as error:
            raise ProviderError(
                "OpenRouter returned an invalid diagnosis response"
            ) from error
        return result.model_copy(
            update={"provider": self.name, "model_version": self.model_version}
        )
