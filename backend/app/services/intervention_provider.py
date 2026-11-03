from app.schemas.interventions import InterventionPersonalization
from app.services.diagnosis_provider import ProviderError
from app.services.openrouter_client import OpenRouterChatClient


class OpenRouterInterventionProvider:
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 20,
        client=None,
        chat_client=None,
        provider_name: str = "openrouter",
    ) -> None:
        self.name = provider_name
        self.client = chat_client or OpenRouterChatClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )

    def personalize(
        self,
        *,
        subject: str = "Mathematics",
        topic: str = "Fractions",
        misconception_code: str,
        taxonomy_description: str,
        learning_objective: str,
        learning_gap: list[str],
        explanation: str,
        instructions: str,
        introduction: str,
        hints: list[str],
    ) -> InterventionPersonalization:
        prompt = (
            "Personalize this short intervention for a learner. Use the "
            "misconception taxonomy and evidence below. Return only the requested "
            "explanation, simple teaching instructions, friendly introduction, and "
            "student hints. Preserve the subject-specific meaning. Do not generate or alter "
            "questions, examples, expected answers, or answer keys.\n"
            f"Subject: {subject}\n"
            f"Topic: {topic}\n"
            f"Misconception: {misconception_code} — {taxonomy_description}\n"
            f"Learning objective: {learning_objective}\n"
            f"Observed learning-gap evidence: {learning_gap}\n"
            f"Template explanation: {explanation}\n"
            f"Template instructions: {instructions}\n"
            f"Template introduction: {introduction}\n"
            f"Template hints: {hints}"
        )
        content = self.client.complete_json(prompt=prompt, temperature=0.2)
        try:
            return InterventionPersonalization.model_validate_json(content)
        except ValueError as error:
            raise ProviderError(
                f"{self.name} returned invalid intervention personalization"
            ) from error


def create_intervention_provider(settings, client=None):
    if settings.ai_provider == "gemini":
        from app.services.gemini_client import GeminiChatClient

        return OpenRouterInterventionProvider(
            api_key="",
            model=settings.gemini_model,
            chat_client=GeminiChatClient.from_settings(settings, client=client),
            provider_name="gemini",
        )
    return OpenRouterInterventionProvider(
        api_key=settings.openrouter_api_key or "",
        model=settings.openrouter_model or "",
        base_url=settings.openrouter_base_url,
        timeout_seconds=settings.openrouter_timeout_seconds,
        client=client,
    )
