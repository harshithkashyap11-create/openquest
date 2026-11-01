import httpx

from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
)


class OpenRouterChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 20,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ProviderConfigurationError(
                "OPENROUTER_API_KEY is required when AI_PROVIDER=openrouter"
            )
        if not model or len(model.split("/")) != 2 or any(
            not part.strip() for part in model.split("/")
        ):
            raise ProviderConfigurationError(
                "OPENROUTER_MODEL must use provider/model format"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client

    def complete_json(self, *, prompt: str, temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self.client is not None:
                response = self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
        except httpx.TimeoutException as error:
            raise ProviderError("OpenRouter request timed out") from error
        except httpx.HTTPError as error:
            raise ProviderError("OpenRouter request failed") from error

        if response.status_code in {401, 403}:
            raise ProviderConfigurationError(
                "OpenRouter authentication failed; check OPENROUTER_API_KEY"
            )
        if response.status_code == 429:
            raise ProviderRateLimited("OpenRouter rate limit exceeded")
        if response.is_error:
            raise ProviderError(
                f"OpenRouter request failed with HTTP {response.status_code}"
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ProviderError(
                "OpenRouter returned an invalid chat completion response"
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderError(
                "OpenRouter returned an invalid chat completion response"
            )
        return content
