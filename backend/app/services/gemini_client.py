"""Native Gemini JSON generation with credentials confined to request headers."""

import re
from threading import local
from time import perf_counter

import httpx

from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
)


class GeminiChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 45,
        client: httpx.Client | None = None,
    ):
        if not api_key:
            raise ProviderConfigurationError(
                "GEMINI_API_KEY is required when AI_PROVIDER=gemini"
            )
        if not model or not re.fullmatch(r"gemini-[A-Za-z0-9._-]+", model):
            raise ProviderConfigurationError(
                "GEMINI_MODEL must be a Gemini model ID without a provider prefix"
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client
        self._metadata = local()

    @property
    def reported_model(self):
        return getattr(self._metadata, "model", None)

    @property
    def latency_ms(self):
        return getattr(self._metadata, "latency_ms", None)

    @classmethod
    def from_settings(cls, settings, client=None):
        return cls(
            api_key=settings.gemini_api_key or "",
            model=settings.gemini_model,
            base_url=settings.gemini_base_url,
            timeout_seconds=settings.gemini_timeout_seconds,
            client=client,
        )

    def complete_json(self, *, prompt: str, temperature: float, attachments: list[dict] | None = None) -> str:
        started = perf_counter()
        url = f"{self.base_url}/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}, *[{"inlineData": item} for item in (attachments or [])]]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature,
                "maxOutputTokens": 8192,
            },
        }
        try:
            if self.client is not None:
                response = self.client.post(
                    url, headers=headers, json=payload, timeout=self.timeout_seconds
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as http:
                    response = http.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as error:
            raise ProviderError("Gemini request timed out. Please retry.") from error
        except httpx.HTTPError as error:
            raise ProviderError("Gemini request failed. Please retry.") from error
        # Never forward upstream bodies or exception URLs: they can contain
        # credential fragments or echoed student messages.
        if response.status_code in {401, 403}:
            raise ProviderConfigurationError(
                "Gemini authentication failed; check the server GEMINI_API_KEY and API restrictions"
            )
        if response.status_code == 429:
            raise ProviderRateLimited(
                "Gemini quota or rate limit exceeded. Please retry later."
            )
        if response.is_error:
            raise ProviderError(
                f"Gemini request failed with HTTP {response.status_code}. Please retry."
            )
        try:
            data = response.json()
            self._metadata.model = data.get("modelVersion") if isinstance(data.get("modelVersion"), str) else None
            self._metadata.latency_ms = round((perf_counter() - started) * 1000)
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(
                part["text"]
                for part in parts
                if isinstance(part, dict)
                and not part.get("thought")
                and isinstance(part.get("text"), str)
            )
        except (ValueError, TypeError, KeyError, IndexError) as error:
            raise ProviderError(
                "Gemini returned an empty, blocked, or invalid response. Please retry."
            ) from error
        if not text.strip():
            raise ProviderError(
                "Gemini returned an empty, blocked, or invalid response. Please retry."
            )
        return text
